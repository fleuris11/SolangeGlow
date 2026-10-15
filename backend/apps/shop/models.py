"""Shops of the pros (module 4): products with variants and stock, delivery options,
cart, orders paid through the secure payment (module 5), promotions, wishlist and alerts.

Amounts are integers in the smallest unit of the shop's currency (`*_minor`).
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.payments.models import Payment


def _media_field(verbose_name, **kwargs):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
        **kwargs,
    )


def _user_fk(related_name, verbose_name, **kwargs):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=kwargs.pop("on_delete", models.CASCADE),
        related_name=related_name,
        verbose_name=verbose_name,
        **kwargs,
    )


class Visibility(models.TextChoices):
    """Moderation state (same values as posts and reviews)."""

    VISIBLE = "visible", _("Visible")
    HELD = "held", _("Held for review")
    REMOVED = "removed", _("Removed")


# --- Reference lists (admin) ---------------------------------------------------------------------


class Category(BaseModel):
    """Product category, edited in the admin. Its key also chooses commission rules."""

    key = models.SlugField(_("key"), max_length=40, unique=True)
    name = models.CharField(_("name"), max_length=80)
    icon = models.CharField(
        _("pictogram"), max_length=40, blank=True, help_text=_("Name of a Phosphor icon.")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("product category")
        verbose_name_plural = _("product categories")
        ordering = ["position", "key"]

    def __str__(self):
        return self.name


class ForbiddenTerm(BaseModel):
    """A word or substance that cannot be sold (blocked) or needs a person to look (review).

    Compared without accents or capitals with the title, description and variants.
    """

    class Action(models.TextChoices):
        BLOCK = "block", _("Block the product")
        REVIEW = "review", _("Send to the review queue")

    term = models.CharField(_("word or substance"), max_length=120)
    normalized = models.CharField(max_length=120, editable=False, db_index=True)
    action = models.CharField(_("what happens"), max_length=6, choices=Action.choices)
    reason = models.CharField(
        _("reason shown to the pro"), max_length=200, help_text=_("For example: banned by ABMed.")
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("forbidden word")
        verbose_name_plural = _("forbidden words")
        ordering = ["action", "term"]

    def __str__(self):
        return self.term

    def save(self, *args, **kwargs):
        from .forbidden import normalize

        self.normalized = normalize(self.term).strip()
        super().save(*args, **kwargs)


# --- The shop of a pro ---------------------------------------------------------------------------


class ShopProfile(BaseModel):
    """How a pro hands over her orders, and whether her shop is open."""

    pro = models.OneToOneField(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="shop", verbose_name=_("pro")
    )
    is_open = models.BooleanField(
        _("open"), default=True, help_text=_("Off: products stay visible, nobody can order.")
    )
    pickup = models.BooleanField(_("pick-up at her place"), default=True)
    pickup_note = models.CharField(_("pick-up hours and details"), max_length=300, blank=True)
    seller_delivery = models.BooleanField(_("she delivers"), default=False)
    partner_delivery = models.BooleanField(_("a partner delivers"), default=False)
    partner_name = models.CharField(
        _("delivery partner"), max_length=80, blank=True, help_text=_("Gozem, a zem, a carrier…")
    )
    return_policy = models.TextField(_("returns and exchanges"), max_length=1000, blank=True)

    class Meta:
        verbose_name = _("shop")
        verbose_name_plural = _("shops")

    def __str__(self):
        return str(self.pro)


class DeliveryMode(models.TextChoices):
    PICKUP = Payment.Delivery.PICKUP.value, _("Pick-up at the seller")
    SELLER = Payment.Delivery.SELLER.value, _("Delivered by the seller")
    PARTNER = Payment.Delivery.PARTNER.value, _("Delivered by a partner")


ZONE_MODES = [
    (DeliveryMode.SELLER.value, DeliveryMode.SELLER.label),
    (DeliveryMode.PARTNER.value, DeliveryMode.PARTNER.label),
]


class DeliveryZone(BaseModel):
    """An area where the pro (or her partner) delivers, with its fee."""

    shop = models.ForeignKey(
        ShopProfile, on_delete=models.CASCADE, related_name="zones", verbose_name=_("shop")
    )
    mode = models.CharField(
        _("delivered by"),
        max_length=10,
        choices=ZONE_MODES,
    )
    name = models.CharField(_("zone"), max_length=80)
    fee_minor = models.BigIntegerField(_("delivery fee"), validators=[MinValueValidator(0)])
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("delivery zone")
        verbose_name_plural = _("delivery zones")
        ordering = ["mode", "position", "name"]

    def __str__(self):
        return self.name


# --- Products ------------------------------------------------------------------------------------


class Product(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("Being checked")
        PUBLISHED = "published", _("Online")
        PAUSED = "paused", _("Paused")
        BLOCKED = "blocked", _("Blocked")
        ARCHIVED = "archived", _("Deleted")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="products", verbose_name=_("pro")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("category"),
    )
    title = models.CharField(_("name"), max_length=120)
    slug = models.SlugField(_("link"), max_length=140)
    description = models.TextField(_("description"), max_length=3000, blank=True)
    description_voice = _media_field(_("description (voice note)"))
    video = _media_field(_("video"))
    currency = models.CharField(_("currency"), max_length=3)
    price_minor = models.BigIntegerField(_("price"), validators=[MinValueValidator(1)])
    prep_days = models.PositiveSmallIntegerField(
        _("preparation (days)"), default=1, help_text=_("Days to prepare before shipping.")
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    visibility = models.CharField(
        _("moderation"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )
    review_reason = models.CharField(_("why it is checked or blocked"), max_length=255, blank=True)
    matched_terms = models.JSONField(_("forbidden words found"), default=list, blank=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True)
    archived_at = models.DateTimeField(_("deleted at"), null=True, blank=True)
    sold_count = models.PositiveIntegerField(_("sold"), default=0)

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["pro", "slug"], name="shop_product_slug_per_pro")
        ]
        indexes = [models.Index(fields=["pro", "status"])]
        permissions = [("review_product", _("Can approve or refuse products"))]

    def __str__(self):
        return self.title

    @property
    def author(self):
        """For moderation: the person who wrote it."""
        return self.pro.user

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}"


class ProductPhoto(BaseModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="photos", verbose_name=_("product")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("photo")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("product photo")
        verbose_name_plural = _("product photos")
        ordering = ["position"]

    def __str__(self):
        return f"{self.product} #{self.position}"


class Variant(BaseModel):
    """A shade, a size or a colour of a product, with its stock (and maybe its price).

    A product without choices has one variant with every field empty.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name=_("product")
    )
    shade = models.CharField(_("shade"), max_length=60, blank=True)
    swatch = models.CharField(
        _("shade colour"),
        max_length=7,
        blank=True,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", _("A colour like #A0522D."))],
    )
    size = models.CharField(_("size"), max_length=30, blank=True)
    color = models.CharField(_("colour"), max_length=40, blank=True)
    price_minor = models.BigIntegerField(
        _("own price"), null=True, blank=True, validators=[MinValueValidator(1)]
    )
    stock = models.PositiveIntegerField(_("stock"), default=0)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("variant")
        verbose_name_plural = _("variants")
        ordering = ["position", "created_at"]

    def __str__(self):
        return f"{self.product} {self.label}".strip()

    @property
    def label(self) -> str:
        return " · ".join(value for value in (self.shade, self.size, self.color) if value)

    @property
    def base_price_minor(self) -> int:
        return self.price_minor or self.product.price_minor


class FlashSale(BaseModel):
    """A price cut between two dates, with a countdown (and maybe a limited quantity)."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="flash_sales", verbose_name=_("product")
    )
    percent_off = models.PositiveSmallIntegerField(
        _("discount (%)"), validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    starts_at = models.DateTimeField(_("starts at"))
    ends_at = models.DateTimeField(_("ends at"))
    quantity_limit = models.PositiveIntegerField(_("quantity on sale"), null=True, blank=True)
    sold_count = models.PositiveIntegerField(_("sold"), default=0)
    announced_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("flash sale")
        verbose_name_plural = _("flash sales")
        ordering = ["-starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="shop_flash_dates"
            )
        ]

    def __str__(self):
        return f"{self.product} -{self.percent_off} %"


class Bundle(BaseModel):
    """A set of products sold together for one price (« lot »)."""

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="bundles", verbose_name=_("pro")
    )
    title = models.CharField(_("name"), max_length=120)
    description = models.TextField(_("description"), max_length=1000, blank=True)
    photo = _media_field(_("photo"))
    currency = models.CharField(_("currency"), max_length=3)
    price_minor = models.BigIntegerField(_("price"), validators=[MinValueValidator(1)])
    is_active = models.BooleanField(_("on sale"), default=True)

    class Meta:
        verbose_name = _("bundle")
        verbose_name_plural = _("bundles")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BundleItem(BaseModel):
    bundle = models.ForeignKey(
        Bundle, on_delete=models.CASCADE, related_name="items", verbose_name=_("bundle")
    )
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="bundle_items", verbose_name=_("variant")
    )
    quantity = models.PositiveSmallIntegerField(
        _("quantity"), default=1, validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = _("bundle item")
        verbose_name_plural = _("bundle items")
        constraints = [
            models.UniqueConstraint(fields=["bundle", "variant"], name="shop_bundle_item_once")
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant}"


class PromoCode(BaseModel):
    """A code created by the pro for her shop (she pays the discount)."""

    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="promo_codes",
        verbose_name=_("pro"),
    )
    code = models.CharField(_("code"), max_length=20)
    percent_off = models.PositiveSmallIntegerField(
        _("discount (%)"), null=True, blank=True, validators=[MinValueValidator(1)]
    )
    amount_off_minor = models.BigIntegerField(
        _("discount (amount)"), null=True, blank=True, validators=[MinValueValidator(1)]
    )
    currency = models.CharField(_("currency"), max_length=3)
    min_order_minor = models.BigIntegerField(_("minimum order"), default=0)
    starts_at = models.DateTimeField(_("from"), null=True, blank=True)
    ends_at = models.DateTimeField(_("until"), null=True, blank=True)
    max_uses = models.PositiveIntegerField(_("uses in total"), null=True, blank=True)
    max_per_client = models.PositiveSmallIntegerField(_("uses per client"), default=1)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("promo code")
        verbose_name_plural = _("promo codes")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["pro", "code"], name="shop_promo_code_per_pro"),
            models.CheckConstraint(
                condition=(
                    Q(percent_off__isnull=False, amount_off_minor__isnull=True)
                    | Q(percent_off__isnull=True, amount_off_minor__isnull=False)
                ),
                name="shop_promo_one_kind",
            ),
        ]

    def __str__(self):
        return self.code


# --- Cart, wishlist, alerts ----------------------------------------------------------------------


class CartItem(BaseModel):
    user = _user_fk("cart_items", _("client"))
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    bundle = models.ForeignKey(
        Bundle, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    quantity = models.PositiveSmallIntegerField(_("quantity"), default=1)

    class Meta:
        verbose_name = _("cart line")
        verbose_name_plural = _("cart lines")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "variant"],
                condition=Q(variant__isnull=False),
                name="shop_cart_variant",
            ),
            models.UniqueConstraint(
                fields=["user", "bundle"],
                condition=Q(bundle__isnull=False),
                name="shop_cart_bundle",
            ),
            models.CheckConstraint(
                condition=(
                    Q(variant__isnull=False, bundle__isnull=True)
                    | Q(variant__isnull=True, bundle__isnull=False)
                ),
                name="shop_cart_one_item",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.variant or self.bundle}"


class WishlistItem(BaseModel):
    user = _user_fk("wishlist", _("client"))
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="wishlisted", verbose_name=_("product")
    )
    price_seen_minor = models.BigIntegerField(_("price when added"))
    price_alerted_at = models.DateTimeField(_("last price alert"), null=True, blank=True)

    class Meta:
        verbose_name = _("wishlist item")
        verbose_name_plural = _("wishlist")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="shop_wishlist_once")
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


class StockAlert(BaseModel):
    """« Tell me when it is back »: removed once the client was told."""

    user = _user_fk("stock_alerts", _("client"))
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, related_name="alerts", verbose_name=_("variant")
    )

    class Meta:
        verbose_name = _("back-in-stock alert")
        verbose_name_plural = _("back-in-stock alerts")
        constraints = [
            models.UniqueConstraint(fields=["user", "variant"], name="shop_stock_alert_once")
        ]

    def __str__(self):
        return f"{self.user} → {self.variant}"


# --- Orders --------------------------------------------------------------------------------------


class Order(BaseModel):
    """What a client bought in one shop. Its money lives in a secure payment (module 5)."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Waiting for payment")
        NEW = "new", _("New")
        PREPARING = "preparing", _("Being prepared")
        SHIPPED = "shipped", _("Shipped")
        READY = "ready", _("Ready to pick up")
        COMPLETED = "completed", _("Handed over")
        CANCELLED = "cancelled", _("Cancelled")
        DISPUTED = "disputed", _("In dispute")
        REFUNDED = "refunded", _("Refunded")

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    buyer = _user_fk("orders", _("client"), on_delete=models.PROTECT)
    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.PROTECT, related_name="orders", verbose_name=_("shop")
    )
    payment = models.OneToOneField(
        Payment, on_delete=models.PROTECT, related_name="order", verbose_name=_("payment")
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    currency = models.CharField(_("currency"), max_length=3)
    subtotal_minor = models.BigIntegerField(_("items before discount"))
    discount_minor = models.BigIntegerField(_("discount"), default=0)
    items_minor = models.BigIntegerField(_("items"))
    delivery_minor = models.BigIntegerField(_("delivery"), default=0)
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("promo code"),
    )
    promo_label = models.CharField(_("code used"), max_length=20, blank=True)
    delivery_mode = models.CharField(_("hand-over"), max_length=10, choices=DeliveryMode.choices)
    zone = models.ForeignKey(
        DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    zone_name = models.CharField(_("zone"), max_length=80, blank=True)
    partner_name = models.CharField(_("delivery partner"), max_length=80, blank=True)
    address = models.CharField(_("address"), max_length=255, blank=True)
    landmarks = models.CharField(_("landmarks"), max_length=500, blank=True)
    contact_phone = models.CharField(_("phone for the delivery"), max_length=20, blank=True)
    note = models.CharField(_("note for the seller"), max_length=300, blank=True)
    prep_days = models.PositiveSmallIntegerField(_("preparation (days)"), default=0)
    shipping_proof = _media_field(_("parcel photo"))
    preparing_at = models.DateTimeField(_("prepared from"), null=True, blank=True)
    completed_at = models.DateTimeField(_("handed over at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    stock_returned = models.BooleanField(default=False, editable=False)
    counted_as_sold = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pro", "status"]),
            models.Index(fields=["buyer", "created_at"]),
        ]

    def __str__(self):
        return self.reference


class OrderLine(BaseModel):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="lines", verbose_name=_("order")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_lines"
    )
    variant = models.ForeignKey(
        Variant, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_lines"
    )
    bundle = models.ForeignKey(
        Bundle, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_lines"
    )
    flash_sale = models.ForeignKey(
        FlashSale, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_lines"
    )
    title = models.CharField(_("name"), max_length=120)
    variant_label = models.CharField(_("choice"), max_length=140, blank=True)
    photo = _media_field(_("photo"))
    category_key = models.CharField(_("category"), max_length=40, blank=True)
    unit_price_minor = models.BigIntegerField(_("unit price"))
    quantity = models.PositiveSmallIntegerField(_("quantity"))
    total_minor = models.BigIntegerField(_("total"))
    # A bundle takes stock from several variants: [{"variant": id, "quantity": n}].
    components = models.JSONField(default=list, blank=True, editable=False)

    class Meta:
        verbose_name = _("order line")
        verbose_name_plural = _("order lines")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity} x {self.title}"
