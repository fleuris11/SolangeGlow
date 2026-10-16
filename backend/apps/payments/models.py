"""Secure payment: double-entry ledger, payments held until the receipt code, refunds,
payouts, disputes, pricing rules and the tax data of the sellers (ADR-007).

Amounts are integers in the smallest unit of their currency (`*_minor`), always with the
currency next to them. The ledger is append-only (database trigger, migration 0002).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


def _user_fk(related_name, verbose_name, **kwargs):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=kwargs.pop("on_delete", models.PROTECT),
        related_name=related_name,
        verbose_name=verbose_name,
        **kwargs,
    )


# --- Ledger --------------------------------------------------------------------------------------


class LedgerAccount(BaseModel):
    """One account per kind, currency and owner (a seller) or provider."""

    class Kind(models.TextChoices):
        PROVIDER_CASH = "provider_cash", _("Cash at the payment provider")
        SELLER_PENDING = "seller_pending", _("Seller — pending")
        FEES_PENDING = "fees_pending", _("Buyer protection — pending")
        SELLER_AVAILABLE = "seller_available", _("Seller — available")
        PAYOUTS_IN_TRANSIT = "payouts_in_transit", _("Payouts in progress")
        REFUNDS_IN_TRANSIT = "refunds_in_transit", _("Refunds in progress")
        COMMISSION_REVENUE = "commission_revenue", _("Revenue — commissions")
        FEE_REVENUE = "fee_revenue", _("Revenue — buyer protection")
        PROVIDER_FEES = "provider_fees", _("Expense — payment fees")

    # Assets and expenses grow on the debit side; the others on the credit side.
    DEBIT_NORMAL = frozenset({Kind.PROVIDER_CASH, Kind.PROVIDER_FEES})
    ESCROW = frozenset({Kind.SELLER_PENDING, Kind.FEES_PENDING})

    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    currency = models.CharField(_("currency"), max_length=3)
    owner = _user_fk("ledger_accounts", _("owner"), null=True, blank=True, on_delete=models.PROTECT)
    provider = models.CharField(_("provider"), max_length=20, blank=True)

    class Meta:
        verbose_name = _("ledger account")
        verbose_name_plural = _("ledger accounts")
        ordering = ["kind", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "currency", "owner", "provider"],
                nulls_distinct=False,
                name="payments_account_unique",
            )
        ]

    def __str__(self):
        who = self.owner or self.provider
        return f"{self.get_kind_display()} {self.currency}" + (f" · {who}" if who else "")

    @property
    def debit_normal(self) -> bool:
        return self.kind in self.DEBIT_NORMAL


class JournalEntry(BaseModel):
    """A balanced set of lines, written once and never changed (corrections are new entries)."""

    kind = models.CharField(_("event"), max_length=40)
    idempotency_key = models.CharField(_("unique key"), max_length=120, unique=True)
    currency = models.CharField(_("currency"), max_length=3)
    description = models.CharField(_("description"), max_length=255, blank=True)
    payment = models.ForeignKey(
        "Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
        verbose_name=_("payment"),
    )
    refund = models.ForeignKey(
        "Refund", on_delete=models.PROTECT, null=True, blank=True, related_name="entries"
    )
    payout = models.ForeignKey(
        "Payout", on_delete=models.PROTECT, null=True, blank=True, related_name="entries"
    )
    # No database constraint: deleting or anonymising a person never touches the ledger.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("by"),
    )

    class Meta:
        verbose_name = _("ledger entry")
        verbose_name_plural = _("ledger entries")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.created_at:%Y-%m-%d %H:%M}"


class JournalLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    entry = models.ForeignKey(
        JournalEntry, on_delete=models.PROTECT, related_name="lines", verbose_name=_("entry")
    )
    account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="lines", verbose_name=_("account")
    )
    debit_minor = models.BigIntegerField(_("debit"), default=0)
    credit_minor = models.BigIntegerField(_("credit"), default=0)

    class Meta:
        verbose_name = _("ledger line")
        verbose_name_plural = _("ledger lines")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(debit_minor__gt=0, credit_minor=0) | Q(debit_minor=0, credit_minor__gt=0)
                ),
                name="payments_line_one_side",
            )
        ]

    def __str__(self):
        side = f"D {self.debit_minor}" if self.debit_minor else f"C {self.credit_minor}"
        return f"{self.account} {side}"


# --- Pricing rules -------------------------------------------------------------------------------


class Purpose(models.TextChoices):
    ORDER = "order", _("Order")
    DEPOSIT = "deposit", _("Booking deposit")
    TRAINING = "training", _("Training")
    SELECTION = "selection", _("France Selection")
    OTHER = "other", _("Other")


class PricingRule(BaseModel):
    """Commission (paid by the seller) or buyer protection fee (paid by the client).

    The most precise rule wins: seller, then category, then country, then purpose.
    """

    class Kind(models.TextChoices):
        COMMISSION = "commission", _("Commission")
        BUYER_PROTECTION = "buyer_protection", _("Buyer protection")

    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    name = models.CharField(_("name"), max_length=120)
    is_active = models.BooleanField(_("active"), default=True)
    country = models.CharField(_("country"), max_length=2, blank=True)
    category = models.CharField(_("category"), max_length=60, blank=True)
    seller = _user_fk("pricing_rules", _("seller"), null=True, blank=True, on_delete=models.CASCADE)
    purpose = models.CharField(_("for"), max_length=10, choices=Purpose.choices, blank=True)
    currency = models.CharField(
        _("currency"),
        max_length=3,
        blank=True,
        help_text=_("Needed for a fixed amount, a minimum or a maximum."),
    )
    percent_bps = models.PositiveIntegerField(
        _("rate (hundredths of a percent)"), default=0, help_text=_("300 = 3 %.")
    )
    fixed_minor = models.BigIntegerField(_("fixed amount"), default=0)
    min_minor = models.BigIntegerField(_("minimum"), null=True, blank=True)
    max_minor = models.BigIntegerField(_("maximum"), null=True, blank=True)
    valid_from = models.DateTimeField(_("from"), null=True, blank=True)
    valid_until = models.DateTimeField(_("until"), null=True, blank=True)
    priority = models.IntegerField(_("priority"), default=0)

    class Meta:
        verbose_name = _("pricing rule")
        verbose_name_plural = _("pricing rules")
        ordering = ["kind", "-priority", "name"]

    def __str__(self):
        return self.name


# --- Payments ------------------------------------------------------------------------------------


class PaymentGroup(BaseModel):
    """Several payments (one per shop of a cart) paid in one go at the provider.

    Each payment keeps its seller, its receipt code and its own ledger entries; only the
    provider's page and its answer are shared.
    """

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    buyer = _user_fk("payment_groups", _("client"))
    currency = models.CharField(_("currency"), max_length=3)
    total_minor = models.BigIntegerField(_("total paid"))
    provider = models.CharField(_("provider"), max_length=20)
    provider_reference = models.CharField(_("provider reference"), max_length=120, blank=True)
    checkout_url = models.TextField(_("payment page"), blank=True)
    expires_at = models.DateTimeField(_("to pay before"), null=True, blank=True)
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)

    class Meta:
        verbose_name = _("grouped payment")
        verbose_name_plural = _("grouped payments")
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference

    @property
    def description(self) -> str:
        return f"Solange Glow {self.reference}"


class Payment(BaseModel):
    """Money of a client, held until she confirms she received her order (receipt code)."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", _("Waiting for payment")
        HELD = "held", _("Paid, money held")
        SHIPPED = "shipped", _("Shipped")
        RELEASED = "released", _("Paid to the seller")
        REFUNDED = "refunded", _("Refunded")
        PARTIALLY_REFUNDED = "partially_refunded", _("Partly refunded")
        DISPUTED = "disputed", _("In dispute")
        CANCELLED = "cancelled", _("Cancelled")

    class Delivery(models.TextChoices):
        PICKUP = "pickup", _("Picked up at the seller")
        SELLER = "seller", _("Delivered by the seller")
        PARTNER = "partner", _("Delivered by a partner")
        SERVICE = "service", _("Service (no delivery)")

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    buyer = _user_fk("purchases", _("client"))
    seller = _user_fk("sales", _("seller"))
    purpose = models.CharField(_("for"), max_length=10, choices=Purpose.choices)
    source_type = models.CharField(_("linked to"), max_length=40, blank=True)
    source_id = models.UUIDField(_("linked id"), null=True, blank=True)
    group = models.ForeignKey(
        PaymentGroup,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("paid with"),
    )
    description = models.CharField(_("description"), max_length=200)
    country = models.CharField(_("country"), max_length=2, blank=True)
    category = models.CharField(_("category"), max_length=60, blank=True)
    currency = models.CharField(_("currency"), max_length=3)
    items_minor = models.BigIntegerField(_("items"))
    delivery_minor = models.BigIntegerField(_("delivery"), default=0)
    buyer_fee_minor = models.BigIntegerField(_("buyer protection"), default=0)
    commission_minor = models.BigIntegerField(_("commission"), default=0)
    total_minor = models.BigIntegerField(_("total paid"))
    refunded_minor = models.BigIntegerField(_("refunded"), default=0)
    commission_rule = models.ForeignKey(
        PricingRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    buyer_fee_rule = models.ForeignKey(
        PricingRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT
    )
    provider = models.CharField(_("provider"), max_length=20)
    provider_reference = models.CharField(_("provider reference"), max_length=120, blank=True)
    checkout_url = models.TextField(_("payment page"), blank=True)
    expires_at = models.DateTimeField(_("to pay before"), null=True, blank=True)
    delivery_mode = models.CharField(
        _("delivery"), max_length=10, choices=Delivery.choices, default=Delivery.SELLER
    )
    carrier = models.CharField(_("carrier"), max_length=80, blank=True)
    tracking_number = models.CharField(_("tracking number"), max_length=80, blank=True)
    expected_delivery_at = models.DateTimeField(_("expected delivery"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    delivery_proof = models.ForeignKey(
        "core.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    service_at = models.DateTimeField(_("appointment"), null=True, blank=True)
    prep_days = models.PositiveSmallIntegerField(
        _("preparation days"),
        default=0,
        help_text=_("Added to the shipping deadline (made-to-order items)."),
    )
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)
    shipped_at = models.DateTimeField(_("shipped at"), null=True, blank=True)
    disputed_at = models.DateTimeField(_("disputed at"), null=True, blank=True)
    released_at = models.DateTimeField(_("released at"), null=True, blank=True)
    refunded_at = models.DateTimeField(_("refunded at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    end_reason = models.CharField(_("reason"), max_length=40, blank=True)
    # Receipt code: hashed to check it, encrypted so the client can see it again.
    receipt_code_hash = models.CharField(max_length=64, blank=True, editable=False)
    receipt_code_secret = models.TextField(blank=True, editable=False)
    receipt_code_attempts = models.PositiveSmallIntegerField(_("code attempts"), default=0)
    receipt_code_renewals = models.PositiveSmallIntegerField(_("new codes"), default=0)
    ship_reminded_at = models.DateTimeField(null=True, blank=True, editable=False)
    release_reminders = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]
        permissions = [("decide_dispute", _("Can decide disputes"))]

    def __str__(self):
        return self.reference

    @property
    def seller_gross_minor(self) -> int:
        """What the seller receives before commission: items and delivery."""
        return self.items_minor + self.delivery_minor


class Refund(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("In progress")
        MANUAL = "manual", _("To do by hand at the provider")
        SUCCEEDED = "succeeded", _("Done")
        FAILED = "failed", _("Failed")

    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name="refunds", verbose_name=_("payment")
    )
    amount_minor = models.BigIntegerField(_("amount"))
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.PENDING
    )
    reason = models.CharField(_("reason"), max_length=40)
    provider_reference = models.CharField(_("provider reference"), max_length=120, blank=True)
    error = models.CharField(_("error"), max_length=255, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("refund")
        verbose_name_plural = _("refunds")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payment} -{self.amount_minor} {self.currency}"


class PayoutMethod(BaseModel):
    """Where a seller receives her money (encrypted details, masked display)."""

    class Kind(models.TextChoices):
        MOBILE_MONEY = "mobile_money", _("Mobile Money")
        STRIPE = "stripe", _("Stripe account")
        FAKE = "fake", _("Test account")

    seller = _user_fk("payout_methods", _("seller"), on_delete=models.CASCADE)
    currency = models.CharField(_("currency"), max_length=3)
    kind = models.CharField(_("type"), max_length=15, choices=Kind.choices)
    details_secret = models.TextField(editable=False)
    display = models.CharField(_("shown as"), max_length=80)

    class Meta:
        verbose_name = _("payout method")
        verbose_name_plural = _("payout methods")
        constraints = [
            models.UniqueConstraint(fields=["seller", "currency"], name="payments_method_unique")
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.display}"


class Payout(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        PROCESSING = "processing", _("In progress")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")

    seller = _user_fk("payouts", _("seller"))
    amount_minor = models.BigIntegerField(_("amount"))
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.REQUESTED
    )
    provider = models.CharField(_("provider"), max_length=20)
    destination = models.CharField(_("destination"), max_length=80)
    provider_reference = models.CharField(_("provider reference"), max_length=120, blank=True)
    error = models.CharField(_("error"), max_length=255, blank=True)
    paid_at = models.DateTimeField(_("paid at"), null=True, blank=True)

    class Meta:
        verbose_name = _("payout")
        verbose_name_plural = _("payouts")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.seller} {self.amount_minor} {self.currency}"


class WebhookEvent(BaseModel):
    """Each event of a provider, once: a second delivery of the same event is ignored."""

    class Status(models.TextChoices):
        PROCESSED = "processed", _("Processed")
        IGNORED = "ignored", _("Ignored")
        FAILED = "failed", _("Failed")

    provider = models.CharField(_("provider"), max_length=20)
    event_id = models.CharField(_("event id"), max_length=120)
    kind = models.CharField(_("type"), max_length=60)
    payload = models.JSONField(_("content"), default=dict)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices)
    error = models.CharField(_("error"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("provider event")
        verbose_name_plural = _("provider events")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "event_id"], name="payments_event_once")
        ]

    def __str__(self):
        return f"{self.provider} {self.kind} {self.event_id}"


# --- Disputes ------------------------------------------------------------------------------------


class Dispute(BaseModel):
    class Reason(models.TextChoices):
        NOT_RECEIVED = "not_received", _("Not received")
        NOT_AS_DESCRIBED = "not_as_described", _("Not as described")
        DAMAGED = "damaged", _("Damaged")
        OTHER = "other", _("Other")
        NO_PROOF = "no_proof", _("No code and no proof of delivery")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        DECIDED = "decided", _("Decided")

    class Decision(models.TextChoices):
        RELEASE = "release", _("Pay the seller")
        REFUND = "refund", _("Refund everything")
        PARTIAL = "partial", _("Refund part")

    payment = models.OneToOneField(
        Payment, on_delete=models.PROTECT, related_name="dispute", verbose_name=_("payment")
    )
    opened_by = _user_fk("+", _("opened by"), null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.CharField(_("reason"), max_length=20, choices=Reason.choices)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.OPEN
    )
    conversation = models.ForeignKey(
        "messaging.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("dispute room"),
    )
    response_due_at = models.DateTimeField(_("answer before"))
    reminded_at = models.DateTimeField(null=True, blank=True, editable=False)
    overdue = models.BooleanField(
        _("answer time over"), default=False, help_text=_("Shown first in the queue.")
    )
    decision = models.CharField(_("decision"), max_length=10, choices=Decision.choices, blank=True)
    refund_minor = models.BigIntegerField(_("refunded"), default=0)
    decided_by = _user_fk("+", _("decided by"), null=True, blank=True, on_delete=models.SET_NULL)
    decided_at = models.DateTimeField(_("decided at"), null=True, blank=True)
    note = models.TextField(_("note for both parties"), blank=True)

    class Meta:
        verbose_name = _("dispute")
        verbose_name_plural = _("disputes")
        ordering = ["-overdue", "response_due_at"]

    def __str__(self):
        return f"{self.payment} — {self.get_reason_display()}"


class DisputeEvidence(BaseModel):
    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="evidence", verbose_name=_("dispute")
    )
    author = _user_fk("+", _("author"), null=True, blank=True, on_delete=models.SET_NULL)
    text = models.TextField(_("text"), blank=True)
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("evidence")
        verbose_name_plural = _("evidence")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.dispute} — {self.author}"


# --- Taxes (DAC7) and reconciliation -------------------------------------------------------------


class SellerTaxProfile(BaseModel):
    """What a platform declares about its sellers each year (DAC7, France)."""

    seller = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tax_profile",
        verbose_name=_("seller"),
    )
    legal_name = models.CharField(_("legal name"), max_length=150)
    is_business = models.BooleanField(_("registered business"), default=False)
    business_name = models.CharField(_("business name"), max_length=150, blank=True)
    birth_date = models.DateField(_("birth date"), null=True, blank=True)
    address = models.CharField(_("address"), max_length=255)
    postal_code = models.CharField(_("postal code"), max_length=20, blank=True)
    city = models.CharField(_("city"), max_length=80)
    country = models.CharField(_("country of residence"), max_length=2)
    tax_id_secret = models.TextField(editable=False, blank=True)
    tax_id_hint = models.CharField(_("tax number"), max_length=20, blank=True)
    vat_number = models.CharField(_("VAT number"), max_length=30, blank=True)

    class Meta:
        verbose_name = _("tax data of a seller")
        verbose_name_plural = _("tax data of the sellers")

    def __str__(self):
        return self.legal_name


class ReconciliationRun(BaseModel):
    provider = models.CharField(_("provider"), max_length=20)
    period_start = models.DateTimeField(_("from"))
    period_end = models.DateTimeField(_("to"))
    checked = models.PositiveIntegerField(_("checked"), default=0)
    discrepancies = models.PositiveIntegerField(_("differences"), default=0)

    class Meta:
        verbose_name = _("reconciliation")
        verbose_name_plural = _("reconciliations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} {self.period_end:%Y-%m-%d}"


class ReconciliationItem(BaseModel):
    class Kind(models.TextChoices):
        MISSING_IN_LEDGER = "missing_in_ledger", _("At the provider, not in the ledger")
        MISSING_AT_PROVIDER = "missing_at_provider", _("In the ledger, not at the provider")
        AMOUNT_MISMATCH = "amount_mismatch", _("Different amounts")

    run = models.ForeignKey(
        ReconciliationRun, on_delete=models.CASCADE, related_name="items", verbose_name=_("run")
    )
    kind = models.CharField(_("type"), max_length=20, choices=Kind.choices)
    reference = models.CharField(_("reference"), max_length=120)
    expected_minor = models.BigIntegerField(_("in the ledger"), null=True, blank=True)
    actual_minor = models.BigIntegerField(_("at the provider"), null=True, blank=True)
    currency = models.CharField(_("currency"), max_length=3)

    class Meta:
        verbose_name = _("difference")
        verbose_name_plural = _("differences")

    def __str__(self):
        return f"{self.get_kind_display()} {self.reference}"
