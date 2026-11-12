"""The back office of the owner (ADR-001, ADR-017): two-factor authentication of the team,
« sign in as » a member (always traced), translations corrected in the database, and the
prospecting of the pros."""

import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class StaffDevice(BaseModel):
    """The authenticator app of a team member (TOTP, RFC 6238). The secret is encrypted."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_device",
        verbose_name=_("team member"),
    )
    secret = models.TextField(_("secret (encrypted)"), editable=False)
    confirmed_at = models.DateTimeField(_("activated at"), null=True, blank=True)
    last_step = models.BigIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = _("two-factor device")
        verbose_name_plural = _("two-factor devices")
        permissions = [
            ("view_dashboard", _("See the dashboard")),
            ("use_moderation_console", _("Use the moderation console")),
            ("use_disputes_console", _("Use the disputes console")),
            ("use_selection_console", _("Use the France Selection console")),
            ("manage_team", _("Manage the team")),
            ("manage_flags", _("Turn features on and off")),
            ("edit_translations", _("Correct the translations")),
            ("impersonate_user", _("Sign in as a member")),
            ("export_csv", _("Export lists")),
        ]

    def __str__(self):
        return str(self.user)


class RecoveryCode(BaseModel):
    """A one-time backup code, kept hashed (when the phone is lost)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recovery_codes"
    )
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)


class Impersonation(BaseModel):
    """A team member signed in as a member, for support. Short, traced, never on staff."""

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonations_done",
        verbose_name=_("team member"),
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="impersonations_received",
        verbose_name=_("member"),
    )
    reason = models.CharField(_("reason"), max_length=200)
    expires_at = models.DateTimeField(_("until"))
    ended_at = models.DateTimeField(_("ended at"), null=True, blank=True)
    actions = models.PositiveIntegerField(_("actions done"), default=0)

    class Meta:
        verbose_name = _("sign-in as a member")
        verbose_name_plural = _("sign-ins as a member")
        ordering = ["-created_at"]


class TranslationOverride(BaseModel):
    """A text of the interface corrected in the admin, used instead of the original one."""

    class Domain(models.TextChoices):
        WEB = "web", _("App (web)")
        SERVER = "server", _("Server (e-mails, errors, admin)")

    domain = models.CharField(_("where"), max_length=8, choices=Domain.choices)
    language = models.CharField(_("language"), max_length=8, choices=settings.LANGUAGES)
    key = models.CharField(
        _("key"),
        max_length=500,
        help_text=_("Web: the key (home.question). Server: the original English text."),
    )
    text = models.TextField(_("text"))
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("by"),
    )

    class Meta:
        verbose_name = _("corrected translation")
        verbose_name_plural = _("corrected translations")
        ordering = ["domain", "key", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "language", "key"], name="backoffice_one_override"
            )
        ]

    def __str__(self):
        return f"{self.language} {self.key}"


def _invite_code() -> str:
    return secrets.token_urlsafe(9)


class Prospect(BaseModel):
    """A pro to win over: imported from a file, invited, followed until she is active."""

    class Status(models.TextChoices):
        NEW = "new", _("To contact")
        CONTACTED = "contacted", _("Contacted")
        SIGNED_UP = "signed_up", _("Signed up")
        ACTIVE = "active", _("Active")
        DECLINED = "declined", _("Not interested")

    name = models.CharField(_("name"), max_length=150)
    business_name = models.CharField(_("business"), max_length=150, blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    city = models.CharField(_("city"), max_length=80, blank=True)
    address = models.CharField(
        _("address"), max_length=200, blank=True, help_text=_("Shown on the prepared showcase.")
    )
    country = models.CharField(_("country"), max_length=2, default="BJ")
    trade = models.CharField(_("trade"), max_length=40, blank=True)
    source = models.CharField(_("source"), max_length=80, blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.NEW, db_index=True
    )
    notes = models.TextField(_("notes"), blank=True)
    language = models.CharField(
        _("language of the messages"), max_length=5, choices=settings.LANGUAGES, default="fr"
    )
    services = models.TextField(
        _("what they do"), blank=True, help_text=_("Their services, their prices, their style.")
    )
    pitch = models.TextField(
        _("our proposal"),
        blank=True,
        help_text=_("One or two sentences written for them; shown in the e-mails ({{ pitch }})."),
    )
    website = models.CharField(
        _("site or social page"), max_length=300, blank=True, help_text=_("Instagram, Facebook…")
    )
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("prepared showcase"),
    )
    last_message_at = models.DateTimeField(_("last e-mail"), null=True, blank=True)
    invite_code = models.CharField(
        _("invitation code"), max_length=20, unique=True, default=_invite_code, editable=False
    )
    invited_at = models.DateTimeField(_("invited at"), null=True, blank=True)
    signed_up_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("account"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("followed by"),
    )

    class Meta:
        verbose_name = _("prospect")
        verbose_name_plural = _("prospects")
        ordering = ["status", "-created_at"]

    def __str__(self):
        return self.business_name or self.name


class ProspectEmailTemplate(BaseModel):
    """A standard e-mail for the prospects, written once per language and edited in the admin.

    Words between braces are replaced: {{ name }}, {{ business }}, {{ city }}, {{ pitch }},
    {{ link }} (their personal link) and {{ stop_link }} (« not interested »).
    """

    key = models.SlugField(_("key"), max_length=40, unique=True)
    name = models.CharField(_("name"), max_length=80)
    subject = models.CharField(_("subject"), max_length=150)
    body = models.TextField(_("text"))
    needs_showcase = models.BooleanField(
        _("needs a prepared showcase"),
        default=False,
        help_text=_("Sent only to a prospect whose showcase was prepared: the link opens it."),
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("standard e-mail")
        verbose_name_plural = _("standard e-mails")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class ProspectMessage(BaseModel):
    """One e-mail sent to a prospect: what was written, when, by whom, and whether it left."""

    class Status(models.TextChoices):
        QUEUED = "queued", _("Leaving")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Not sent")

    prospect = models.ForeignKey(
        Prospect, on_delete=models.CASCADE, related_name="messages", verbose_name=_("prospect")
    )
    template_key = models.CharField(_("standard e-mail"), max_length=40, blank=True)
    to_email = models.EmailField(_("to"))
    subject = models.CharField(_("subject"), max_length=200)
    body = models.TextField(_("text"))
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.QUEUED
    )
    error = models.CharField(_("error"), max_length=200, blank=True)
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("by"),
    )

    class Meta:
        verbose_name = _("e-mail sent to a prospect")
        verbose_name_plural = _("e-mails sent to prospects")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.to_email} · {self.subject}"
