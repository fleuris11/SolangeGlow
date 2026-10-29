"""France Selection (module 6): trendy products bought in France by the platform and sent to
Benin. Purchase prices are in euro cents, sale prices in FCFA (integers, see pricing.py).
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.payments.models import Payment


def _media_field(verbose_name):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
    )


class Aisle(models.TextChoices):
    SMALL_PRICES = "small_prices", _("Small prices")
    TRENDING = "trending", _("Trending")
    LUXURY = "luxury", _("Luxury")


class ShippingMode(models.TextChoices):
    GROUPED = "grouped", _("Weekly grouped shipment")
    EXPRESS = "express", _("Express")


def _optional_amount(verbose_name, help_text=""):
    return models.PositiveIntegerField(
        verbose_name, null=True, blank=True, help_text=help_text or _("Empty: the default value.")
    )


class SelectionCategory(BaseModel):
    """A category with its price parameters (empty fields take the default settings)."""

    key = models.SlugField(_("key"), max_length=40, unique=True)
    name = models.CharField(_("name"), max_length=80)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    air_restricted = models.BooleanField(
        _("forbidden by air"),
        default=False,
        help_text=_("Perfumes, aerosols: blocked while the setting says so."),
    )
    transport_per_kg_cents = _optional_amount(_("transport per kg, grouped (euro cents)"))
    express_per_kg_cents = _optional_amount(_("transport per kg, express (euro cents)"))
    packaging_cents = _optional_amount(_("packaging (euro cents)"))
    customs_bps = _optional_amount(
        _("estimated customs (hundredths of a percent)"), _("2000 = 20 %. Empty: the default.")
    )
    margin_bps = _optional_amount(
        _("margin (hundredths of a percent)"), _("2500 = 25 %. Empty: the default.")
    )
    payment_fee_cents = _optional_amount(_("payment fees (euro cents)"))

    class Meta:
        verbose_name = _("Selection category")
        verbose_name_plural = _("Selection categories")
        ordering = ["position", "key"]

    def __str__(self):
        return self.name


class SelectionProduct(BaseModel):
    class Availability(models.TextChoices):
        AVAILABLE = "available", _("Available")
        OUT_OF_STOCK = "out_of_stock", _("Out of stock at the merchant")
        HIDDEN = "hidden", _("Hidden")

    title = models.CharField(_("name"), max_length=140)
    slug = models.SlugField(_("link"), max_length=160, unique=True)
    merchant_name = models.CharField(_("merchant"), max_length=80)
    merchant_url = models.URLField(_("link to the merchant"), max_length=500)
    purchase_price_cents = models.PositiveIntegerField(
        _("purchase price (euro cents)"), validators=[MinValueValidator(1)]
    )
    weight_grams = models.PositiveIntegerField(_("weight (grams)"))
    description = models.TextField(_("description"), max_length=3000, blank=True)
    aisle = models.CharField(_("aisle"), max_length=12, choices=Aisle.choices)
    category = models.ForeignKey(
        SelectionCategory,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("category"),
    )
    availability = models.CharField(
        _("availability"),
        max_length=12,
        choices=Availability.choices,
        default=Availability.AVAILABLE,
        db_index=True,
    )
    options = models.JSONField(
        _("choices"),
        default=list,
        blank=True,
        help_text=_('Shades or sizes the client chooses from, for example ["230", "240"].'),
    )
    # Computed by the pricing engine (recalculated in the admin, frozen in each order).
    price_xof = models.PositiveIntegerField(_("price (FCFA)"), default=0, editable=False)
    express_price_xof = models.PositiveIntegerField(
        _("express price (FCFA)"), null=True, blank=True, editable=False
    )
    priced_at = models.DateTimeField(_("priced at"), null=True, blank=True, editable=False)
    sold_count = models.PositiveIntegerField(_("sold"), default=0, editable=False)

    class Meta:
        verbose_name = _("Selection product")
        verbose_name_plural = _("Selection products")
        ordering = ["aisle", "-created_at"]

    def __str__(self):
        return self.title


class SelectionPhoto(BaseModel):
    product = models.ForeignKey(
        SelectionProduct, on_delete=models.CASCADE, related_name="photos", verbose_name=_("product")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("photo")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("photo")
        verbose_name_plural = _("photos")
        ordering = ["position", "created_at"]

    def __str__(self):
        return f"{self.product} #{self.position}"


class PickupPoint(BaseModel):
    """Where clients pick up their parcel in Benin (against their receipt code)."""

    name = models.CharField(_("name"), max_length=80)
    city = models.CharField(_("city"), max_length=80)
    address = models.CharField(_("address"), max_length=200)
    landmarks = models.CharField(_("landmarks"), max_length=300, blank=True)
    hours = models.CharField(_("opening hours"), max_length=120, blank=True)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("pick-up point")
        verbose_name_plural = _("pick-up points")
        ordering = ["position", "city", "name"]

    def __str__(self):
        return f"{self.name} ({self.city})"


class Shipment(BaseModel):
    """A parcel batch from France to Benin (the weekly grouped one, or an express one)."""

    class Status(models.TextChoices):
        PREPARING = "preparing", _("Being prepared")
        DEPARTED = "departed", _("On its way")
        ARRIVED = "arrived", _("Arrived in Benin")

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    mode = models.CharField(_("mode"), max_length=8, choices=ShippingMode.choices)
    carrier = models.CharField(_("carrier"), max_length=80, blank=True)
    tracking_number = models.CharField(_("tracking number"), max_length=80, blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.PREPARING
    )
    departed_at = models.DateTimeField(_("left at"), null=True, blank=True)
    arrived_at = models.DateTimeField(_("arrived at"), null=True, blank=True)
    note = models.CharField(_("note"), max_length=200, blank=True)

    class Meta:
        verbose_name = _("shipment")
        verbose_name_plural = _("shipments")
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference


class GroupBuy(BaseModel):
    """A product that leaves when enough clients ordered it, for a lower price."""

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        REACHED = "reached", _("Goal reached")
        FAILED = "failed", _("Goal not reached")

    product = models.ForeignKey(
        SelectionProduct,
        on_delete=models.PROTECT,
        related_name="group_buys",
        verbose_name=_("product"),
    )
    target_quantity = models.PositiveIntegerField(
        _("goal (items)"), validators=[MinValueValidator(2)]
    )
    price_xof = models.PositiveIntegerField(_("group price (FCFA)"))
    ends_at = models.DateTimeField(_("ends at"))
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    closed_at = models.DateTimeField(_("closed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("group pre-order")
        verbose_name_plural = _("group pre-orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product} ({self.target_quantity})"


class SpecialRequest(BaseModel):
    """« Find me this »: a link or a photo from a client, a quote from the team."""

    class Status(models.TextChoices):
        NEW = "new", _("To quote")
        QUOTED = "quoted", _("Quote sent")
        ORDERED = "ordered", _("Ordered")
        DECLINED = "declined", _("Declined")
        EXPIRED = "expired", _("Expired")
        REFUSED = "refused", _("Not possible")

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="selection_requests",
        verbose_name=_("client"),
    )
    link = models.URLField(_("link"), max_length=500, blank=True)
    photo = _media_field(_("photo"))
    note = models.TextField(_("her words"), max_length=1000, blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    # The quote, filled in the admin.
    title = models.CharField(_("product"), max_length=140, blank=True)
    merchant_name = models.CharField(_("merchant"), max_length=80, blank=True)
    merchant_url = models.URLField(_("link to buy"), max_length=500, blank=True)
    purchase_price_cents = models.PositiveIntegerField(
        _("purchase price (euro cents)"), null=True, blank=True
    )
    weight_grams = models.PositiveIntegerField(_("weight (grams)"), null=True, blank=True)
    category = models.ForeignKey(
        SelectionCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("category"),
    )
    price_xof = models.PositiveIntegerField(
        _("quoted price (FCFA)"),
        null=True,
        blank=True,
        help_text=_("Empty: the price of the formula."),
    )
    answer = models.CharField(_("message to the client"), max_length=500, blank=True)
    quoted_at = models.DateTimeField(_("quoted at"), null=True, blank=True)
    valid_until = models.DateTimeField(_("valid until"), null=True, blank=True)

    class Meta:
        verbose_name = _("special request")
        verbose_name_plural = _("special requests")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.link or str(self.pk)


class SelectionOrder(BaseModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Waiting for payment")
        WAITING_GROUP = "waiting_group", _("Waiting for the group")
        TO_ORDER = "to_order", _("To order at the merchant")
        ORDERED = "ordered", _("Ordered at the merchant")
        RECEIVED = "received", _("Received in France")
        SHIPPED = "shipped", _("On its way to Benin")
        ARRIVED = "arrived", _("Ready at the pick-up point")
        COMPLETED = "completed", _("Handed over")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")
        DISPUTED = "disputed", _("In dispute")

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="selection_orders",
        verbose_name=_("client"),
    )
    payment = models.OneToOneField(
        Payment, on_delete=models.PROTECT, related_name="selection_order", verbose_name=_("payment")
    )
    product = models.ForeignKey(
        SelectionProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("product"),
    )
    special_request = models.OneToOneField(
        SpecialRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
        verbose_name=_("special request"),
    )
    group_buy = models.ForeignKey(
        GroupBuy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("group pre-order"),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    title = models.CharField(_("product"), max_length=140)
    option = models.CharField(_("choice"), max_length=60, blank=True)
    quantity = models.PositiveSmallIntegerField(_("quantity"), default=1)
    unit_price_xof = models.PositiveIntegerField(_("unit price (FCFA)"))
    total_xof = models.PositiveIntegerField(_("total (FCFA)"))
    # A Glow voucher (module 10): paid by the platform, which sells.
    discount_xof = models.PositiveIntegerField(_("Glow voucher (FCFA)"), default=0)
    shipping_mode = models.CharField(_("shipping"), max_length=8, choices=ShippingMode.choices)
    pickup_point = models.ForeignKey(
        PickupPoint,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("pick-up point"),
    )
    merchant_name = models.CharField(_("merchant"), max_length=80)
    merchant_url = models.URLField(_("link to the merchant"), max_length=500)
    purchase_price_cents = models.PositiveIntegerField(_("purchase price (euro cents)"))
    merchant_order_number = models.CharField(_("merchant order number"), max_length=80, blank=True)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("shipment"),
    )
    estimate_from = models.DateField(_("expected from"), null=True, blank=True)
    estimate_to = models.DateField(_("expected until"), null=True, blank=True)
    ordered_at = models.DateTimeField(_("ordered at"), null=True, blank=True)
    received_at = models.DateTimeField(_("received in France at"), null=True, blank=True)
    shipped_at = models.DateTimeField(_("left at"), null=True, blank=True)
    arrived_at = models.DateTimeField(_("arrived at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("handed over at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)

    class Meta:
        verbose_name = _("Selection order")
        verbose_name_plural = _("Selection orders")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["buyer", "created_at"])]

    def __str__(self):
        return self.reference
