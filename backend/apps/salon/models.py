"""What a salon manages besides the agenda: packages of sessions, installments, gift cards,
stock, payments taken on the spot, marketing consents and campaigns."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Channel(models.TextChoices):
    EMAIL = "email", _("E-mail")
    WHATSAPP = "whatsapp", _("WhatsApp")


# --- Packages and installments ------------------------------------------------------------------


class Package(BaseModel):
    """« 5 facials »: sessions of a service paid in advance, used one by one."""

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="packages", verbose_name=_("pro")
    )
    service = models.ForeignKey(
        "pros.Service", on_delete=models.CASCADE, related_name="packages", verbose_name=_("service")
    )
    name = models.CharField(_("name"), max_length=80)
    sessions = models.PositiveSmallIntegerField(
        _("sessions"), validators=[MinValueValidator(2), MaxValueValidator(50)]
    )
    price_minor = models.PositiveIntegerField(_("price"))
    currency = models.CharField(_("currency"), max_length=3)
    validity_days = models.PositiveSmallIntegerField(_("valid for (days)"), default=365)
    max_installments = models.PositiveSmallIntegerField(
        _("payable in up to"), default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    is_active = models.BooleanField(_("on sale"), default=True)

    class Meta:
        verbose_name = _("package")
        verbose_name_plural = _("packages")

    def __str__(self):
        return self.name


class ClientPackage(BaseModel):
    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting for the payment")
        ACTIVE = "active", _("In use")
        USED_UP = "used_up", _("All sessions used")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    package = models.ForeignKey(
        Package, on_delete=models.PROTECT, related_name="sold", verbose_name=_("package")
    )
    pro = models.ForeignKey("pros.ProProfile", on_delete=models.CASCADE, related_name="+")
    record = models.ForeignKey(
        "booking.ClientRecord",
        on_delete=models.CASCADE,
        related_name="packages",
        verbose_name=_("client file"),
    )
    client = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    sessions_total = models.PositiveSmallIntegerField(_("sessions"))
    sessions_used = models.PositiveSmallIntegerField(_("sessions used"), default=0)
    price_minor = models.PositiveIntegerField(_("price"))
    currency = models.CharField(_("currency"), max_length=3)
    expires_on = models.DateField(_("valid until"))
    status = models.CharField(_("status"), max_length=10, choices=Status.choices)

    class Meta:
        verbose_name = _("package of a client")
        verbose_name_plural = _("packages of clients")

    @property
    def sessions_left(self) -> int:
        return self.sessions_total - self.sessions_used

    def __str__(self):
        return f"{self.package} — {self.record}"


class PackageUse(BaseModel):
    client_package = models.ForeignKey(ClientPackage, on_delete=models.CASCADE, related_name="uses")
    appointment = models.OneToOneField(
        "booking.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="package_use",
    )
    note = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = _("session used")
        verbose_name_plural = _("sessions used")


class InstallmentPlan(BaseModel):
    """Paying in several times: a package, or a big service (a wedding)."""

    class Status(models.TextChoices):
        RUNNING = "running", _("Running")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")

    pro = models.ForeignKey("pros.ProProfile", on_delete=models.CASCADE, related_name="+")
    record = models.ForeignKey(
        "booking.ClientRecord", on_delete=models.CASCADE, related_name="installment_plans"
    )
    client_package = models.OneToOneField(
        ClientPackage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="installment_plan",
    )
    label = models.CharField(_("for"), max_length=120)
    total_minor = models.PositiveIntegerField(_("total"))
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default="running")

    class Meta:
        verbose_name = _("payment in several times")
        verbose_name_plural = _("payments in several times")


class Installment(BaseModel):
    class Status(models.TextChoices):
        DUE = "due", _("To pay")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")

    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name="installments")
    position = models.PositiveSmallIntegerField()
    due_on = models.DateField(_("due on"))
    amount_minor = models.PositiveIntegerField(_("amount"))
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default="due")
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="installment",
    )
    on_site = models.OneToOneField(
        "salon.OnSitePayment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="installment",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    reminded_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["plan", "position"]
        verbose_name = _("installment")
        verbose_name_plural = _("installments")


# --- Gift cards ---------------------------------------------------------------------------------


class GiftCard(BaseModel):
    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting for the payment")
        ACTIVE = "active", _("Usable")
        USED_UP = "used_up", _("Used up")
        EXPIRED = "expired", _("Expired")
        CANCELLED = "cancelled", _("Cancelled")

    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="gift_cards",
        verbose_name=_("pro"),
    )
    code = models.CharField(_("code"), max_length=12, unique=True)
    amount_minor = models.PositiveIntegerField(_("amount"))
    balance_minor = models.PositiveIntegerField(_("balance"))
    currency = models.CharField(_("currency"), max_length=3)
    buyer = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_cards_bought",
        verbose_name=_("bought by"),
    )
    from_name = models.CharField(_("from"), max_length=80, blank=True)
    recipient_name = models.CharField(_("for"), max_length=80)
    recipient_contact = models.CharField(_("sent to"), max_length=120, blank=True)
    message = models.CharField(_("message"), max_length=300, blank=True)
    expires_on = models.DateField(_("valid until"))
    status = models.CharField(_("status"), max_length=10, choices=Status.choices)
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_card",
    )
    sold_on_site = models.BooleanField(_("sold at the salon"), default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("gift card")
        verbose_name_plural = _("gift cards")

    def __str__(self):
        return self.code


class GiftCardUse(BaseModel):
    card = models.ForeignKey(GiftCard, on_delete=models.CASCADE, related_name="uses")
    amount_minor = models.PositiveIntegerField(_("amount"))
    appointment = models.ForeignKey(
        "booking.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gift_card_uses",
    )
    online = models.BooleanField(_("online"), default=False)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("use of a gift card")
        verbose_name_plural = _("uses of gift cards")
        ordering = ["-created_at"]


# --- Stock --------------------------------------------------------------------------------------


class StockItem(BaseModel):
    class Kind(models.TextChoices):
        RETAIL = "retail", _("Sold to clients")
        PROFESSIONAL = "professional", _("Used in the salon")

    class Unit(models.TextChoices):
        PIECE = "piece", _("pieces")
        ML = "ml", _("ml")
        G = "g", _("g")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="stock", verbose_name=_("pro")
    )
    name = models.CharField(_("name"), max_length=120)
    ean = models.CharField(_("barcode"), max_length=14, blank=True, db_index=True)
    kind = models.CharField(_("type"), max_length=12, choices=Kind.choices)
    unit = models.CharField(_("unit"), max_length=6, choices=Unit.choices, default="piece")
    quantity = models.IntegerField(_("in stock"), default=0)
    alert_threshold = models.PositiveIntegerField(_("alert under"), default=0)
    variant = models.OneToOneField(
        "shop.Variant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_item",
        verbose_name=_("product of the shop"),
        help_text=_("Linked: the stock is the one of the shop."),
    )
    cost_minor = models.PositiveIntegerField(_("cost price"), null=True, blank=True)
    is_active = models.BooleanField(_("followed"), default=True)
    alerted_on = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("stock item")
        verbose_name_plural = _("stock items")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["pro", "ean"], condition=~models.Q(ean=""), name="salon_one_item_per_ean"
            )
        ]

    def __str__(self):
        return self.name


class StockMovement(BaseModel):
    class Kind(models.TextChoices):
        IN = "in", _("Delivery")
        OUT = "out", _("Taken out")
        SALE = "sale", _("Sold")
        USE = "use", _("Used for a service")
        INVENTORY = "inventory", _("Inventory")
        LOSS = "loss", _("Lost or broken")

    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(_("type"), max_length=10, choices=Kind.choices)
    change = models.IntegerField(_("change"))
    after = models.IntegerField(_("stock after"))
    appointment = models.ForeignKey(
        "booking.Appointment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.CharField(_("note"), max_length=120, blank=True)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("stock movement")
        verbose_name_plural = _("stock movements")
        ordering = ["-created_at"]


class ServiceConsumption(BaseModel):
    """What a service uses: « colour = 1 tube + 30 ml of developer »."""

    service = models.ForeignKey(
        "pros.Service", on_delete=models.CASCADE, related_name="consumptions"
    )
    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="consumptions")
    quantity = models.PositiveIntegerField(_("quantity"), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _("product used by a service")
        verbose_name_plural = _("products used by services")
        constraints = [
            models.UniqueConstraint(fields=["service", "item"], name="salon_one_use_per_item")
        ]


# --- Payments taken on the spot -----------------------------------------------------------------


class OnSitePayment(BaseModel):
    """Money the pro took herself (cash, Mobile Money, her card terminal). It never goes
    through the platform: kept for her dashboard and receipts. Not a certified till."""

    class Method(models.TextChoices):
        CASH = "cash", _("Cash")
        MOMO = "momo", _("Mobile Money")
        CARD = "card", _("Card (terminal)")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="on_site_payments"
    )
    appointment = models.ForeignKey(
        "booking.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="on_site_payments",
    )
    record = models.ForeignKey(
        "booking.ClientRecord", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    label = models.CharField(_("for"), max_length=120)
    amount_minor = models.PositiveIntegerField(_("amount"), validators=[MinValueValidator(1)])
    currency = models.CharField(_("currency"), max_length=3)
    method = models.CharField(_("paid with"), max_length=10, choices=Method.choices)
    reference = models.CharField(_("transaction number"), max_length=60, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    cancel_reason = models.CharField(_("why"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("payment at the salon")
        verbose_name_plural = _("payments at the salon")
        ordering = ["-created_at"]


# --- Consents and campaigns ---------------------------------------------------------------------


class MarketingConsent(BaseModel):
    """Yes or no to the salon's offers on a channel, with when and how it was given."""

    class Source(models.TextChoices):
        BOOKING = "booking", _("Ticked when booking")
        PRO = "pro", _("Noted by the pro with her agreement")
        UNSUBSCRIBE = "unsubscribe", _("Unsubscribe link")
        CLIENT = "client", _("Changed by the client")

    record = models.ForeignKey(
        "booking.ClientRecord", on_delete=models.CASCADE, related_name="consents"
    )
    channel = models.CharField(_("channel"), max_length=10, choices=Channel.choices)
    granted = models.BooleanField(_("agrees"))
    source = models.CharField(_("how"), max_length=12, choices=Source.choices)
    changed_at = models.DateTimeField(_("when"))

    class Meta:
        verbose_name = _("marketing consent")
        verbose_name_plural = _("marketing consents")
        constraints = [
            models.UniqueConstraint(fields=["record", "channel"], name="salon_one_consent")
        ]


class Campaign(BaseModel):
    class Segment(models.TextChoices):
        INACTIVE = "inactive", _("Not come for a while")
        BIRTHDAY = "birthday", _("Birthday in the next 7 days")
        PACKAGE_LOW = "package_low", _("Package almost used")
        ALL = "all", _("All my clients")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SENT = "sent", _("Sent")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="campaigns", verbose_name=_("pro")
    )
    name = models.CharField(_("name"), max_length=80)
    segment = models.CharField(_("who"), max_length=12, choices=Segment.choices)
    inactive_days = models.PositiveSmallIntegerField(_("not come for (days)"), default=60)
    channel = models.CharField(_("channel"), max_length=10, choices=Channel.choices)
    subject = models.CharField(_("subject"), max_length=120, blank=True)
    body = models.TextField(_("message"), max_length=1000)
    status = models.CharField(_("status"), max_length=6, choices=Status.choices, default="draft")
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    targeted = models.PositiveIntegerField(_("in the segment"), default=0)
    without_consent = models.PositiveIntegerField(_("left out (no consent)"), default=0)

    class Meta:
        verbose_name = _("campaign")
        verbose_name_plural = _("campaigns")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CampaignMessage(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Not sent")

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="messages")
    record = models.ForeignKey("booking.ClientRecord", on_delete=models.CASCADE, related_name="+")
    destination = models.CharField(max_length=160)
    status = models.CharField(max_length=8, choices=Status.choices, default="pending")
    error = models.CharField(max_length=200, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "record"], name="salon_one_message")
        ]
