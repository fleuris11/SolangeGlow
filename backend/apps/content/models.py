"""Contents edited by the owner (module 12, ADR-017): pages (help, terms, privacy…), home
banners, the FAQ, their versions, and the tickets of the help center."""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Page(BaseModel):
    class Kind(models.TextChoices):
        HELP = "help", _("Help")
        TERMS = "terms", _("Terms and conditions")
        PRIVACY = "privacy", _("Privacy")
        LEGAL = "legal", _("Legal notice")
        GAME_RULES = "game_rules", _("Rules of the games")
        RETURNS = "returns", _("Returns and refunds")
        OTHER = "other", _("Other")

    slug = models.SlugField(_("link"), max_length=80, unique=True)
    kind = models.CharField(_("kind"), max_length=12, choices=Kind.choices, default=Kind.OTHER)
    title = models.CharField(_("title"), max_length=150)
    summary = models.CharField(_("summary"), max_length=300, blank=True)
    body = models.TextField(
        _("text"),
        help_text=_("Paragraphs separated by an empty line; a line starting with # is a title."),
    )
    is_published = models.BooleanField(_("published"), default=True)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    version = models.PositiveIntegerField(_("version"), default=1, editable=False)

    class Meta:
        verbose_name = _("page")
        verbose_name_plural = _("pages")
        ordering = ["position", "title"]

    def __str__(self):
        return self.title


class Banner(BaseModel):
    """An editorial message at the top of the home page (not an ad: no « Sponsored »)."""

    title = models.CharField(_("title"), max_length=90)
    text = models.CharField(_("text"), max_length=200, blank=True)
    cta = models.CharField(_("button"), max_length=30, blank=True)
    link = models.CharField(_("link"), max_length=300, blank=True)
    image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("picture"),
    )
    countries = models.JSONField(
        _("countries"), default=list, blank=True, help_text=_('e.g. ["BJ"]. Empty: everywhere.')
    )
    starts_at = models.DateTimeField(_("from"), null=True, blank=True)
    ends_at = models.DateTimeField(_("until"), null=True, blank=True)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    version = models.PositiveIntegerField(_("version"), default=1, editable=False)

    class Meta:
        verbose_name = _("home banner")
        verbose_name_plural = _("home banners")
        ordering = ["position", "-created_at"]

    def __str__(self):
        return self.title


class FaqItem(BaseModel):
    class Topic(models.TextChoices):
        ACCOUNT = "account", _("My account")
        BOOKING = "booking", _("Appointments")
        PAYMENT = "payment", _("Payments and refunds")
        SHOP = "shop", _("Shops and orders")
        SELECTION = "selection", _("France Selection")
        GIFTS = "gifts", _("Gifts")
        PROS = "pros", _("For the pros")
        GAMES = "games", _("Glow Points and games")

    topic = models.CharField(_("topic"), max_length=10, choices=Topic.choices)
    question = models.CharField(_("question"), max_length=200)
    answer = models.TextField(_("answer"))
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_published = models.BooleanField(_("published"), default=True)
    version = models.PositiveIntegerField(_("version"), default=1, editable=False)

    class Meta:
        verbose_name = _("question of the FAQ")
        verbose_name_plural = _("FAQ")
        ordering = ["topic", "position"]

    def __str__(self):
        return self.question


class ContentVersion(BaseModel):
    """A copy of a content (all its languages) at each save, to read or bring back."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.CharField(max_length=64, db_index=True)
    target = GenericForeignKey("content_type", "object_id")
    number = models.PositiveIntegerField(_("version"))
    data = models.JSONField(_("content"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("by"),
    )

    class Meta:
        verbose_name = _("version")
        verbose_name_plural = _("versions")
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "number"], name="content_one_version"
            )
        ]


class Ticket(BaseModel):
    """A question sent from « Contact us », answered by the team from the admin."""

    class Status(models.TextChoices):
        NEW = "new", _("New")
        ANSWERED = "answered", _("Answered")
        CLOSED = "closed", _("Closed")

    reference = models.CharField(_("reference"), max_length=12, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="help_tickets",
        verbose_name=_("account"),
    )
    name = models.CharField(_("name"), max_length=120)
    email = models.EmailField(_("e-mail"), blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    topic = models.CharField(_("topic"), max_length=10, choices=FaqItem.Topic.choices, blank=True)
    message = models.TextField(_("message"), max_length=3000)
    language = models.CharField(_("language"), max_length=8, default="fr")
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    answer = models.TextField(_("answer"), blank=True)
    answered_at = models.DateTimeField(_("answered at"), null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("answered by"),
    )

    class Meta:
        verbose_name = _("help ticket")
        verbose_name_plural = _("help tickets")
        ordering = ["status", "-created_at"]

    def __str__(self):
        return self.reference
