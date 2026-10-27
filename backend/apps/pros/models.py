from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, GistIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.media.storage import identity_vault_storage
from apps.core.models import BaseModel


class Trade(BaseModel):
    """A beauty or fashion trade (makeup, braids…). The list is edited in the admin."""

    class Icon(models.TextChoices):
        MAKEUP = "makeup", _("Lipstick")
        HAIR = "hair", _("Comb")
        BRAIDS = "braids", _("Braid")
        NAILS = "nails", _("Nail polish")
        SEWING = "sewing", _("Thread spool")
        HEADWRAP = "headwrap", _("Headwrap")
        SKINCARE = "skincare", _("Cream jar")

    key = models.SlugField(_("key"), max_length=40, unique=True)
    name = models.CharField(_("name"), max_length=80)
    icon = models.CharField(_("pictogram"), max_length=20, choices=Icon.choices)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("trade")
        verbose_name_plural = _("trades")
        ordering = ["position", "key"]

    def __str__(self):
        return self.name


class SpokenLanguage(models.TextChoices):
    """Languages a pro speaks with her clients (shown on her showcase, used in search)."""

    FRENCH = "fr", _("French")
    ENGLISH = "en", _("English")
    FON = "fon", _("Fon")
    YORUBA = "yo", _("Yoruba")
    GOUN = "guw", _("Goun")
    MINA = "gej", _("Mina")
    EWE = "ee", _("Ewe")
    BARIBA = "bba", _("Bariba")
    DENDI = "ddn", _("Dendi")
    HAUSA = "ha", _("Hausa")
    WOLOF = "wo", _("Wolof")
    LINGALA = "ln", _("Lingala")
    ARABIC = "ar", _("Arabic")
    SPANISH = "es", _("Spanish")
    PORTUGUESE = "pt", _("Portuguese")
    SLOVAK = "sk", _("Slovak")


class SocialNetwork(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    TIKTOK = "tiktok", "TikTok"
    FACEBOOK = "facebook", "Facebook"
    WHATSAPP = "whatsapp", "WhatsApp"
    YOUTUBE = "youtube", "YouTube"
    WEBSITE = "website", _("Website")


def _media_field(verbose_name):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
    )


class ProProfile(BaseModel):
    """Professional side of an account: her showcase. One account can be client and pro."""

    class Kind(models.TextChoices):
        INDEPENDENT = "independent", _("Independent")
        BUSINESS = "business", _("Salon or business")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        SUSPENDED = "suspended", _("Suspended")

    class Verification(models.TextChoices):
        NONE = "none", _("Not sent")
        PENDING = "pending", _("Waiting for review")
        VERIFIED = "verified", _("Verified pro")
        REJECTED = "rejected", _("Refused")

    class LocationSource(models.TextChoices):
        MAP = "map", _("Placed on the map")
        GPS = "gps", _("Phone GPS")
        ADMIN = "admin", _("Set by the team")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pro_profile",
        verbose_name=_("account"),
    )
    kind = models.CharField(
        _("type"), max_length=12, choices=Kind.choices, default=Kind.INDEPENDENT
    )
    business_name = models.CharField(_("business name"), max_length=80, blank=True)
    slug = models.SlugField(
        _("short link"),
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        help_text=_("solangeglow.com/<short link>: lowercase letters, digits and dashes."),
    )
    trades = models.ManyToManyField(
        Trade, blank=True, related_name="pros", verbose_name=_("trades")
    )
    bio = models.TextField(_("presentation"), max_length=1000, blank=True)
    bio_voice = _media_field(_("presentation (voice note)"))
    photo = _media_field(_("photo"))
    cover = _media_field(_("cover picture"))
    social_links = models.JSONField(
        _("social networks"), default=dict, blank=True, help_text=_("Network: link or handle.")
    )
    languages = ArrayField(
        models.CharField(max_length=4, choices=SpokenLanguage.choices),
        default=list,
        blank=True,
        verbose_name=_("languages spoken"),
    )

    # Where clients find her. The point is required to appear in searches by distance.
    country = models.ForeignKey(
        "core.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pros",
        verbose_name=_("country"),
    )
    currency = models.CharField(_("currency"), max_length=3, blank=True)
    city = models.CharField(_("city"), max_length=80, blank=True)
    district = models.CharField(_("district"), max_length=80, blank=True)
    address = models.CharField(_("address"), max_length=200, blank=True)
    location = gis_models.PointField(_("position"), geography=True, null=True, blank=True)
    location_source = models.CharField(
        _("position given by"), max_length=8, choices=LocationSource.choices, blank=True
    )
    receives_clients = models.BooleanField(
        _("receives clients"),
        default=True,
        help_text=_("Off: she only goes to her clients; her address and position stay private."),
    )
    itinerary_video = _media_field(_("itinerary video"))
    landmarks = models.TextField(_("landmarks"), max_length=500, blank=True)
    landmarks_voice = _media_field(_("landmarks (voice note)"))

    # Home visits: a radius around her position, or an area drawn on the map.
    travels_to_clients = models.BooleanField(_("goes to the client's home"), default=False)
    service_radius_km = models.PositiveSmallIntegerField(
        _("travel radius (km)"), null=True, blank=True
    )
    service_area = gis_models.PolygonField(_("travel area"), geography=True, null=True, blank=True)
    travel_fee_minor = models.BigIntegerField(
        _("travel fee"),
        null=True,
        blank=True,
        help_text=_("In the smallest unit of the currency (FCFA, cents)."),
    )

    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(_("published at"), null=True, blank=True)
    suspended_at = models.DateTimeField(_("suspended at"), null=True, blank=True)
    suspension_reason = models.TextField(_("reason of the suspension"), blank=True)
    verification_status = models.CharField(
        _("verification"),
        max_length=10,
        choices=Verification.choices,
        default=Verification.NONE,
        db_index=True,
    )
    verified_at = models.DateTimeField(_("verified at"), null=True, blank=True)
    # « Trained on Solange Glow »: she finished a course that counts for the badge (module 7).
    trained_at = models.DateTimeField(_("trained on Solange Glow since"), null=True, blank=True)

    # Filled by the reviews module.
    rating_average = models.DecimalField(
        _("average rating"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MaxValueValidator(5)],
    )
    rating_count = models.PositiveIntegerField(_("number of reviews"), default=0)

    # Search: unaccented words (name, trades in every language, places, services).
    search_document = models.TextField(_("search words"), blank=True, editable=False)
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        verbose_name = _("pro profile")
        verbose_name_plural = _("pro profiles")
        indexes = [
            GistIndex(fields=["location"], name="pros_profile_location_gist"),
            GinIndex(fields=["search_vector"], name="pros_profile_search_gin"),
            GinIndex(
                fields=["search_document"],
                opclasses=["gin_trgm_ops"],
                name="pros_profile_search_trgm",
            ),
        ]

    def __str__(self):
        return self.business_name or str(self.user)

    @property
    def display_name(self) -> str:
        return self.business_name or self.user.first_name or ""

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def is_verified(self) -> bool:
        return self.verification_status == self.Verification.VERIFIED

    @property
    def is_trained(self) -> bool:
        return self.trained_at is not None


class ServiceCategory(BaseModel):
    """A pro's own way of grouping her services ("Tresses", "Soins du visage")."""

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="categories", verbose_name=_("pro")
    )
    name = models.CharField(_("name"), max_length=60)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("service category")
        verbose_name_plural = _("service categories")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class Service(BaseModel):
    """A service on the pro's price list, booked later (module 8) or shown in a post.

    Its time is made of ordered steps (work, then waiting time while a product acts…):
    the booking module will chain them and assign each step to a collaborator.
    """

    class PriceKind(models.TextChoices):
        FIXED = "fixed", _("Fixed price")
        FROM = "from", _("From")
        QUOTE = "quote", _("On quote")

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="services", verbose_name=_("pro")
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name=_("category"),
    )
    trade = models.ForeignKey(
        Trade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name=_("trade"),
    )
    name = models.CharField(_("name"), max_length=80)
    description = models.TextField(_("description"), max_length=1000, blank=True)
    price_kind = models.CharField(
        _("price"), max_length=8, choices=PriceKind.choices, default=PriceKind.FIXED
    )
    price_minor = models.BigIntegerField(
        _("amount"),
        null=True,
        blank=True,
        help_text=_("In the smallest unit of the currency. Empty for a quote."),
    )
    currency = models.CharField(_("currency"), max_length=3)
    duration_minutes = models.PositiveIntegerField(
        _("total duration (min)"), default=0, help_text=_("Sum of the steps.")
    )
    available_at_home = models.BooleanField(_("also at the client's home"), default=False)
    # Module 8: the deposit asked when booking (paid through the secure payment).
    deposit_kind = models.CharField(
        _("deposit"),
        max_length=8,
        choices=[("none", _("None")), ("amount", _("Amount")), ("percent", _("Percentage"))],
        default="none",
    )
    deposit_value = models.PositiveIntegerField(
        _("deposit value"),
        default=0,
        help_text=_("An amount in the smallest unit, or a percentage (100 = paid in full)."),
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("shown"), default=True)
    archived_at = models.DateTimeField(_("archived at"), null=True, blank=True)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ["position", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price_kind="quote") | models.Q(price_minor__gte=0),
                name="pros_service_price_given",
            )
        ]

    def __str__(self):
        return self.name

    @property
    def work_minutes(self) -> int:
        return sum(s.duration_minutes for s in self.steps.all() if s.kind == ServiceStep.Kind.WORK)

    @property
    def waiting_minutes(self) -> int:
        return sum(s.duration_minutes for s in self.steps.all() if s.kind == ServiceStep.Kind.WAIT)


class ServiceStep(BaseModel):
    class Kind(models.TextChoices):
        WORK = "work", _("Work")
        WAIT = "wait", _("Waiting time (product acting)")

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="steps", verbose_name=_("service")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    kind = models.CharField(_("type"), max_length=4, choices=Kind.choices, default=Kind.WORK)
    label = models.CharField(_("label"), max_length=60, blank=True)
    duration_minutes = models.PositiveIntegerField(_("duration (min)"))
    # Module 8: steps that need someone (work) are assigned to a collaborator.
    needs_staff = models.BooleanField(_("needs someone"), default=True)
    other_staff_ok = models.BooleanField(
        _("another person may do it"),
        default=False,
        help_text=_("The step can be done by someone else than the previous one."),
    )

    class Meta:
        verbose_name = _("step")
        verbose_name_plural = _("steps")
        ordering = ["position"]

    def __str__(self):
        return self.label or self.get_kind_display()


class ServiceOption(BaseModel):
    """An extra the client can choose ("hair extensions provided"): price and time added."""

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="options", verbose_name=_("service")
    )
    name = models.CharField(_("name"), max_length=80)
    price_minor = models.BigIntegerField(_("extra price"), default=0)
    extra_minutes = models.PositiveIntegerField(_("extra time (min)"), default=0)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("option")
        verbose_name_plural = _("options")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class ServicePhoto(BaseModel):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="photos", verbose_name=_("service")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("picture")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("service picture")
        verbose_name_plural = _("service pictures")
        ordering = ["position", "created_at"]


class OpeningPeriod(BaseModel):
    """Open from `opens_at` to `closes_at` on a weekday; two periods = a break between."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="opening_periods", verbose_name=_("pro")
    )
    weekday = models.PositiveSmallIntegerField(_("day"), choices=Weekday.choices)
    opens_at = models.TimeField(_("opens at"))
    closes_at = models.TimeField(_("closes at"))

    class Meta:
        verbose_name = _("opening hours")
        verbose_name_plural = _("opening hours")
        ordering = ["weekday", "opens_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(closes_at__gt=models.F("opens_at")),
                name="pros_opening_closes_after_opening",
            )
        ]

    def __str__(self):
        return f"{self.get_weekday_display()} {self.opens_at:%H:%M}-{self.closes_at:%H:%M}"


class Closure(BaseModel):
    """Exceptional closure (holidays, a funeral, a training): whole days, both included."""

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="closures", verbose_name=_("pro")
    )
    starts_on = models.DateField(_("from"))
    ends_on = models.DateField(_("to"))
    reason = models.CharField(_("reason"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("closure")
        verbose_name_plural = _("closures")
        ordering = ["starts_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="pros_closure_ends_after_start",
            )
        ]

    def __str__(self):
        return f"{self.starts_on} - {self.ends_on}"


class PortfolioItem(BaseModel):
    """A picture or video of her work; with a "before", it is shown as a before/after pair."""

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="portfolio", verbose_name=_("pro")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("result")
    )
    before_media = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("before"),
    )
    caption = models.CharField(_("caption"), max_length=200, blank=True)
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolio_items",
        verbose_name=_("service"),
    )
    position = models.PositiveIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("portfolio item")
        verbose_name_plural = _("portfolio")
        ordering = ["position", "-created_at"]

    def __str__(self):
        return self.caption or str(self.pk)


def vault_upload_to(instance, filename):
    return f"pros/{instance.pro_id}/{instance.pk}/{filename}"


class ProVerification(BaseModel):
    """Identity document + selfie sent by a pro, reviewed by the verification team.

    The files are encrypted before they reach the vault storage (ADR-005) and are
    only read through `services.read_verification_file`, which records each access.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting for review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Refused")

    class DocumentType(models.TextChoices):
        ID_CARD = "id_card", _("Identity card")
        PASSPORT = "passport", _("Passport")
        RESIDENCE_PERMIT = "residence_permit", _("Residence permit")
        DRIVING_LICENCE = "driving_licence", _("Driving licence")

    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE, related_name="verifications", verbose_name=_("pro")
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    document_type = models.CharField(
        _("document"), max_length=20, choices=DocumentType.choices, default=DocumentType.ID_CARD
    )
    document_file = models.FileField(
        _("identity document"), storage=identity_vault_storage, upload_to=vault_upload_to
    )
    selfie_file = models.FileField(
        _("selfie"), storage=identity_vault_storage, upload_to=vault_upload_to
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("reviewed by"),
    )
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    rejection_reason = models.TextField(
        _("reason of the refusal"), blank=True, help_text=_("Sent to the pro.")
    )

    class Meta:
        verbose_name = _("identity check")
        verbose_name_plural = _("identity checks")
        ordering = ["-created_at"]
        permissions = [("review_identity", _("Can see identity documents and verify pros"))]

    def __str__(self):
        return f"{self.pro} ({self.get_status_display()})"
