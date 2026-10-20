"""Glow Pro offers: the free plan and Premium, their prices by country, the subscription of
each pro, and the white-label booking widget."""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Feature(models.TextChoices):
    """What a plan unlocks (checked by `selectors.has_feature`)."""

    EXTRA_STAFF = "extra_staff", _("More people in the agenda")
    CLIENT_FILE = "client_file", _("Complete client file")
    STOCK = "stock", _("Stock")
    DASHBOARD = "dashboard_full", _("Complete dashboard")
    CAMPAIGNS = "campaigns", _("Campaigns")
    WIDGET = "widget", _("Booking widget")
    EINVOICE = "einvoice", _("Electronic invoices")


class Plan(BaseModel):
    """An offer. Its limits are numbers the code reads (e.g. {"staff": 2})."""

    key = models.SlugField(_("key"), max_length=30, unique=True)
    name = models.CharField(_("name"), max_length=60)
    description = models.TextField(_("what she gets"), blank=True)
    is_default = models.BooleanField(
        _("plan of every pro"), default=False, help_text=_("The free plan: one only.")
    )
    features = models.JSONField(_("unlocked features"), default=list, blank=True)
    limits = models.JSONField(
        _("limits"),
        default=dict,
        blank=True,
        help_text=_('For example {"staff": 2, "campaigns_per_month": 4}. Empty: no limit.'),
    )
    trial_days = models.PositiveSmallIntegerField(_("free trial (days)"), default=0)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("offered"), default=True)

    class Meta:
        verbose_name = _("Glow Pro plan")
        verbose_name_plural = _("Glow Pro plans")
        ordering = ["position", "key"]

    def __str__(self):
        return self.name


class PlanPrice(BaseModel):
    """The monthly price of a plan in a country (euros in France, FCFA in Benin)."""

    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="prices", verbose_name=_("plan")
    )
    country = models.ForeignKey(
        "core.Country", on_delete=models.CASCADE, related_name="+", verbose_name=_("country")
    )
    currency = models.CharField(_("currency"), max_length=3)
    amount_minor = models.PositiveIntegerField(
        _("price per month"), validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = _("price")
        verbose_name_plural = _("prices")
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "country"], name="glowpro_one_price_per_country"
            )
        ]

    def __str__(self):
        return f"{self.plan} {self.country_id}"


class Subscription(BaseModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", _("Free trial")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Waiting for the payment")
        ENDED = "ended", _("Back to the free plan")

    pro = models.OneToOneField(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="glowpro",
        verbose_name=_("pro"),
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions", verbose_name=_("plan")
    )
    status = models.CharField(_("status"), max_length=10, choices=Status.choices)
    trial_used = models.BooleanField(_("trial used"), default=False)
    current_period_end = models.DateTimeField(_("paid until"), null=True, blank=True)
    grace_until = models.DateTimeField(_("grace until"), null=True, blank=True)
    cancel_at_period_end = models.BooleanField(_("stops at the end of the month"), default=False)
    renewal_payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("payment to make"),
    )
    renewal_noticed_at = models.DateTimeField(null=True, blank=True)
    next_plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")

    def __str__(self):
        return f"{self.pro} — {self.plan}"


class SubscriptionPeriod(BaseModel):
    """One paid month (the history of payments of a subscription)."""

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="periods",
        verbose_name=_("subscription"),
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
    starts_at = models.DateTimeField(_("from"))
    ends_at = models.DateTimeField(_("to"))
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subscription_period",
        verbose_name=_("payment"),
    )
    is_trial = models.BooleanField(_("trial"), default=False)

    class Meta:
        verbose_name = _("paid period")
        verbose_name_plural = _("paid periods")
        ordering = ["-starts_at"]


class Widget(BaseModel):
    """The booking module a salon puts on her own website (Premium)."""

    pro = models.OneToOneField(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="widget", verbose_name=_("pro")
    )
    color = models.CharField(_("main colour"), max_length=7, default="#C8102E")
    allowed_domains = models.JSONField(
        _("allowed websites"),
        default=list,
        blank=True,
        help_text=_('Domains only, for example ["salon-estelle.fr", "www.salon-estelle.fr"].'),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("booking widget")
        verbose_name_plural = _("booking widgets")

    def __str__(self):
        return str(self.pro)
