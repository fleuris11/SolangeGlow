"""The advertising network of the platform (module 12, ADR-016): campaigns sold to brands,
shops and pros, boosts paid by the pros, house promotions when nothing is sold.

An impression is counted when an ad is sent to a screen (no tracking script), a click
through a redirect link, a conversion when the person buys or books within a few days
after a click. Counters are kept per day, creative and placement.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Placement(models.TextChoices):
    HOME_BANNER = "home_banner", _("Banner at the top of the home page")
    FEED = "feed", _("Sponsored post in the feed")
    PRODUCT = "product", _("Sponsored product")
    SEARCH = "search", _("Pro shown first in the search")
    SPLASH = "splash", _("Screen when the app opens")


class Advertiser(BaseModel):
    class Kind(models.TextChoices):
        BRAND = "brand", _("Brand")
        BUSINESS = "business", _("Local business")
        PRO = "pro", _("Pro of Solange Glow")
        HOUSE = "house", _("Solange Glow (own promotions)")

    name = models.CharField(_("name"), max_length=120)
    kind = models.CharField(_("kind"), max_length=10, choices=Kind.choices, default=Kind.BRAND)
    contact_name = models.CharField(_("contact"), max_length=120, blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    pro = models.OneToOneField(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="advertiser",
        verbose_name=_("pro"),
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("advertiser")
        verbose_name_plural = _("advertisers")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Campaign(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        ENDED = "ended", _("Ended")

    class Kind(models.TextChoices):
        SOLD = "sold", _("Sold to an advertiser")
        BOOST = "boost", _("Boost paid by a pro")
        HOUSE = "house", _("House promotion (when nothing is sold)")

    class Pricing(models.TextChoices):
        FLAT = "flat", _("Flat price")
        PER_THOUSAND = "per_thousand", _("Per thousand impressions")

    advertiser = models.ForeignKey(
        Advertiser, on_delete=models.PROTECT, related_name="campaigns", verbose_name=_("advertiser")
    )
    name = models.CharField(_("name"), max_length=120)
    kind = models.CharField(_("kind"), max_length=8, choices=Kind.choices, default=Kind.SOLD)
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    starts_at = models.DateTimeField(_("from"))
    ends_at = models.DateTimeField(_("until"))
    priority = models.PositiveSmallIntegerField(
        _("priority"),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("1 to 10: the higher, the more often it is chosen."),
    )
    pricing = models.CharField(
        _("price"), max_length=12, choices=Pricing.choices, default=Pricing.FLAT
    )
    price_minor = models.BigIntegerField(_("price (smallest unit)"), default=0)
    currency = models.CharField(_("currency"), max_length=3, default="XOF")
    impressions_bought = models.PositiveIntegerField(
        _("impressions bought"),
        null=True,
        blank=True,
        help_text=_("Empty: no limit. Reached: the campaign stops."),
    )
    max_per_day = models.PositiveSmallIntegerField(
        _("times a day per person"), default=3, validators=[MinValueValidator(1)]
    )
    countries = models.JSONField(
        _("countries"), default=list, blank=True, help_text=_('e.g. ["BJ"]. Empty: everywhere.')
    )
    cities = models.JSONField(
        _("cities"), default=list, blank=True, help_text=_('e.g. ["Cotonou"]. Empty: everywhere.')
    )
    languages = models.JSONField(
        _("languages"), default=list, blank=True, help_text=_('e.g. ["fr"]. Empty: every language.')
    )
    roles = models.JSONField(
        _("people"),
        default=list,
        blank=True,
        help_text=_('"client" and/or "pro". Empty: everyone.'),
    )
    trades = models.JSONField(
        _("trades"),
        default=list,
        blank=True,
        help_text=_('Trade keys, e.g. ["braids"]. Empty: every trade.'),
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("campaign")
        verbose_name_plural = _("campaigns")
        ordering = ["-starts_at"]

    def __str__(self):
        return self.name


class Creative(BaseModel):
    """What is shown: an image, a short video, a carousel, or a native post (a pro, a
    product, a post of the feed)."""

    class Format(models.TextChoices):
        IMAGE = "image", _("Image")
        VIDEO = "video", _("Short video")
        CAROUSEL = "carousel", _("Carousel")
        NATIVE = "native", _("Native post")

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="creatives", verbose_name=_("campaign")
    )
    name = models.CharField(_("name"), max_length=120)
    format = models.CharField(_("format"), max_length=10, choices=Format.choices)
    placements = models.JSONField(_("placements"), default=list)
    title = models.CharField(_("title"), max_length=80, blank=True)
    text = models.CharField(_("text"), max_length=200, blank=True)
    cta = models.CharField(_("button"), max_length=30, blank=True)
    link = models.CharField(
        _("link"),
        max_length=300,
        blank=True,
        help_text=_("A page of the app (/aicha, /selection…) or a full https:// address."),
    )
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("pro shown"),
    )
    product = models.ForeignKey(
        "shop.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("product shown"),
    )
    selection_product = models.ForeignKey(
        "selection_france.SelectionProduct",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("France Selection product shown"),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("creative")
        verbose_name_plural = _("creatives")
        ordering = ["campaign", "created_at"]

    def __str__(self):
        return self.name


class CreativeMedia(BaseModel):
    creative = models.ForeignKey(Creative, on_delete=models.CASCADE, related_name="media_items")
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.PROTECT, related_name="+", verbose_name=_("media")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("picture or video")
        verbose_name_plural = _("pictures and videos")
        ordering = ["position"]


class AdStat(BaseModel):
    day = models.DateField(_("day"), db_index=True)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="stats", verbose_name=_("campaign")
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.CASCADE, related_name="stats", verbose_name=_("creative")
    )
    placement = models.CharField(_("placement"), max_length=12, choices=Placement.choices)
    impressions = models.PositiveIntegerField(_("impressions"), default=0)
    clicks = models.PositiveIntegerField(_("clicks"), default=0)
    conversions = models.PositiveIntegerField(_("conversions"), default=0)

    class Meta:
        verbose_name = _("statistics of a day")
        verbose_name_plural = _("statistics")
        ordering = ["-day"]
        constraints = [
            models.UniqueConstraint(
                fields=["day", "creative", "placement"], name="ads_one_stat_per_day"
            )
        ]


class AdClick(BaseModel):
    """A click, kept a few days to find the purchase or booking that follows."""

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="clicks")
    creative = models.ForeignKey(Creative, on_delete=models.CASCADE, related_name="clicks")
    placement = models.CharField(max_length=12, choices=Placement.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    conversion = models.CharField(max_length=60, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"], name="ads_click_user")]


class Boost(BaseModel):
    """A pro pays to be shown first (search, feed) for a day or a week."""

    class Duration(models.TextChoices):
        DAY = "day", _("One day")
        WEEK = "week", _("One week")

    class Status(models.TextChoices):
        WAITING_PAYMENT = "waiting_payment", _("Waiting for the payment")
        ACTIVE = "active", _("Running")
        ENDED = "ended", _("Ended")
        CANCELLED = "cancelled", _("Not paid")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="boosts", verbose_name=_("pro")
    )
    duration = models.CharField(_("duration"), max_length=4, choices=Duration.choices)
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.WAITING_PAYMENT
    )
    amount_minor = models.BigIntegerField(_("price"))
    currency = models.CharField(_("currency"), max_length=3)
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("payment"),
    )
    campaign = models.OneToOneField(
        Campaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boost",
        verbose_name=_("campaign"),
    )
    starts_at = models.DateTimeField(_("from"), null=True, blank=True)
    ends_at = models.DateTimeField(_("until"), null=True, blank=True)

    class Meta:
        verbose_name = _("boost")
        verbose_name_plural = _("boosts")
        ordering = ["-created_at"]
