"""Diaspora gifts (module 9, ADR-014): someone abroad pays in euros, a person in Benin
receives a service, a product or a Glow gift card, used in FCFA.

The euros are a payment of their own (purpose « gift », sold by the platform). Each use
in Benin is a payment in FCFA paid by the gift (internal provider « gift »): its money is
held and released like any other one, and a refund comes back onto the gift.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Occasion(models.TextChoices):
    NONE = "none", _("No occasion")
    MOTHERS_DAY = "mothers_day", _("Mother's day")
    WEDDING = "wedding", _("Wedding")
    BIRTHDAY = "birthday", _("Birthday")
    YEAR_END = "year_end", _("End of year celebrations")


def _media(verbose_name):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
    )


class Gift(BaseModel):
    class Kind(models.TextChoices):
        SERVICE = "service", _("A service")
        PRODUCT = "product", _("A product of a shop")
        SELECTION = "selection", _("A France Selection product")
        CARD = "card", _("Glow gift card")

    class Status(models.TextChoices):
        WAITING_PAYMENT = "waiting_payment", _("Waiting for the payment")
        SCHEDULED = "scheduled", _("Paid, sent on the chosen day")
        SENT = "sent", _("Sent")
        OPENED = "opened", _("Opened")
        USED = "used", _("Used")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Not paid")
        REFUNDED = "refunded", _("Cancelled and refunded")

    class Proof(models.TextChoices):
        NONE = "", _("No photo yet")
        SENT = "sent", _("Photo sent")
        DECLINED = "declined", _("Not sent")

    # A gift that can still be used (or booked again after a refund).
    LIVE = frozenset({Status.SENT, Status.OPENED, Status.USED})

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    kind = models.CharField(_("type"), max_length=10, choices=Kind.choices)
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.WAITING_PAYMENT
    )
    giver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gifts_given",
        verbose_name=_("offered by"),
    )
    from_name = models.CharField(_("from"), max_length=80)
    recipient_name = models.CharField(_("for"), max_length=80)
    recipient_phone = models.CharField(_("phone of the person"), max_length=20)
    recipient_email = models.EmailField(_("e-mail of the person"), blank=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gifts_received",
        verbose_name=_("account of the person"),
    )
    language = models.CharField(_("language of the person"), max_length=5, default="fr")
    occasion = models.CharField(
        _("occasion"), max_length=16, choices=Occasion.choices, default=Occasion.NONE
    )
    message = models.CharField(_("message"), max_length=500, blank=True)
    message_media = _media(_("voice or video message"))
    send_at = models.DateTimeField(_("to send on"))
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    opened_at = models.DateTimeField(_("opened at"), null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, editable=False)
    code = models.CharField(_("code"), max_length=12, unique=True)
    # What the gift is worth in Benin, and what is left of it (FCFA).
    currency = models.CharField(_("currency"), max_length=3, default="XOF")
    value_minor = models.BigIntegerField(_("value"))
    balance_minor = models.BigIntegerField(_("left"))
    # What the person abroad paid for it, before the fee (cents), and at which rate.
    price_minor = models.BigIntegerField(_("price"))
    price_currency = models.CharField(_("paid in"), max_length=3, default="EUR")
    rate = models.CharField(_("rate EUR/XOF"), max_length=20)
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gift",
        verbose_name=_("payment in euros"),
    )
    # The offered thing (one of them, by kind).
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gifts",
        verbose_name=_("pro"),
    )
    service = models.ForeignKey(
        "pros.Service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gifts",
        verbose_name=_("service"),
    )
    variant = models.ForeignKey(
        "shop.Variant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gifts",
        verbose_name=_("product"),
    )
    quantity = models.PositiveSmallIntegerField(_("quantity"), default=1)
    delivery_mode = models.CharField(_("hand-over"), max_length=10, blank=True)
    zone = models.ForeignKey(
        "shop.DeliveryZone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("delivery zone"),
    )
    delivery_minor = models.BigIntegerField(_("delivery"), default=0)
    selection_product = models.ForeignKey(
        "selection_france.SelectionProduct",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gifts",
        verbose_name=_("France Selection product"),
    )
    option = models.CharField(_("choice"), max_length=60, blank=True)
    title = models.CharField(_("what"), max_length=200)
    expires_on = models.DateField(_("valid until"))
    cancel_until = models.DateTimeField(_("can be cancelled until"), null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True, editable=False)
    # Proof of joy: a photo of the result, sent only when the person says yes.
    proof_media = _media(_("photo sent"))
    proof_status = models.CharField(
        _("photo"), max_length=10, choices=Proof.choices, default=Proof.NONE, blank=True
    )
    proof_sent_at = models.DateTimeField(_("photo sent at"), null=True, blank=True)
    proof_asked_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("gift")
        verbose_name_plural = _("gifts")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "send_at"])]

    def __str__(self):
        return self.reference


class GiftUse(BaseModel):
    """A payment in FCFA paid by the gift (a booking, an order, a purchase with the card)."""

    gift = models.ForeignKey(Gift, on_delete=models.PROTECT, related_name="uses")
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="gift_use",
        verbose_name=_("payment"),
    )
    amount_minor = models.BigIntegerField(_("amount"))
    refunded_minor = models.BigIntegerField(_("given back"), default=0)
    label = models.CharField(_("for"), max_length=200)
    source_type = models.CharField(_("linked to"), max_length=40, blank=True)
    source_id = models.UUIDField(_("linked id"), null=True, blank=True)

    class Meta:
        verbose_name = _("use of a gift")
        verbose_name_plural = _("uses of gifts")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.gift} — {self.label}"


class GiftCredit(BaseModel):
    """Money given back onto a gift by a refund (once per refund)."""

    use = models.ForeignKey(GiftUse, on_delete=models.PROTECT, related_name="credits")
    refund = models.OneToOneField(
        "payments.Refund", on_delete=models.PROTECT, related_name="+", verbose_name=_("refund")
    )
    amount_minor = models.BigIntegerField(_("amount"))

    class Meta:
        verbose_name = _("money given back to a gift")
        verbose_name_plural = _("money given back to gifts")


class GiftPhoto(BaseModel):
    """A photo of the result, waiting for the person to say whether it goes to the giver."""

    class Source(models.TextChoices):
        PRO = "pro", _("Taken by the pro")
        RECIPIENT = "recipient", _("Sent by the person")

    gift = models.ForeignKey(Gift, on_delete=models.CASCADE, related_name="photos")
    media = models.ForeignKey("core.MediaAsset", on_delete=models.CASCADE, related_name="+")
    source = models.CharField(_("from"), max_length=10, choices=Source.choices)

    class Meta:
        verbose_name = _("photo of a gift")
        verbose_name_plural = _("photos of gifts")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["gift", "media"], name="gifts_photo_once"),
        ]
