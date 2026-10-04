import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.choices import Role
from apps.core.models import BaseModel

from .managers import UserManager, normalize_email


def default_roles():
    return [Role.CLIENT]


def avatar_upload_to(instance, filename):
    # Kept for the 0003 migration; photos now live in core.MediaAsset.
    return f"avatars/{instance.pk}/{uuid.uuid4().hex}.webp"


class SignupChannel(models.TextChoices):
    PHONE = "phone", _("Phone")
    EMAIL = "email", _("E-mail")
    ADMIN = "admin", _("Created in the admin")


class Theme(models.TextChoices):
    SYSTEM = "system", _("Like the device")
    LIGHT = "light", _("Light")
    DARK = "dark", _("Dark")


class TextSize(models.TextChoices):
    NORMAL = "normal", _("Normal")
    LARGE = "large", _("Large")
    XLARGE = "xlarge", _("Extra large")


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    """A person using Solange Glow.

    Signs in with a phone number (E.164) or an e-mail address: both are optional,
    at least one is required, and each is unique.
    """

    phone = PhoneNumberField(
        _("phone number"),
        unique=True,
        null=True,
        blank=True,
        help_text=_("International format, e.g. +229 01 97 00 00 00."),
    )
    email = models.EmailField(_("e-mail address"), unique=True, null=True, blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    country = models.ForeignKey(
        "core.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("country"),
    )
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=8,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    preferred_currency = models.ForeignKey(
        "core.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("preferred currency"),
    )
    # Display preferences, mirrored from the web app once the user is signed in.
    theme = models.CharField(_("theme"), max_length=8, choices=Theme.choices, default=Theme.SYSTEM)
    text_size = models.CharField(
        _("text size"), max_length=8, choices=TextSize.choices, default=TextSize.NORMAL
    )
    data_saver = models.BooleanField(_("data saver"), default=False)
    audio_mode = models.BooleanField(
        _("audio mode"),
        default=False,
        help_text=_("Shows buttons that read important texts aloud."),
    )

    roles = ArrayField(
        models.CharField(max_length=16, choices=Role.choices),
        default=default_roles,
        verbose_name=_("roles"),
    )

    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(
        _("admin access"),
        default=False,
        help_text=_("Can sign in to the back office."),
    )

    city = models.CharField(_("city"), max_length=80, blank=True)
    birth_date = models.DateField(_("date of birth"), null=True, blank=True)
    photo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("photo"),
    )

    notify_whatsapp = models.BooleanField(_("WhatsApp notifications"), default=True)
    notify_email = models.BooleanField(_("e-mail notifications"), default=True)
    notify_push = models.BooleanField(_("push notifications"), default=True)
    # Quiet hours, in the time zone of the country. Empty = platform default.
    quiet_hours_start = models.TimeField(_("quiet hours start"), null=True, blank=True)
    quiet_hours_end = models.TimeField(_("quiet hours end"), null=True, blank=True)

    signup_channel = models.CharField(
        _("sign-up channel"), max_length=8, choices=SignupChannel.choices, blank=True
    )
    phone_verified_at = models.DateTimeField(_("phone verified at"), null=True, blank=True)
    email_verified_at = models.DateTimeField(_("e-mail verified at"), null=True, blank=True)
    onboarded_at = models.DateTimeField(_("welcome completed at"), null=True, blank=True)
    # Every token issued before this moment is refused ("sign out on every device").
    tokens_revoked_at = models.DateTimeField(_("tokens revoked at"), null=True, blank=True)
    # Deletion asked: the account is erased after the grace period unless she signs in again.
    deletion_requested_at = models.DateTimeField(_("deletion requested at"), null=True, blank=True)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__isnull=False) | models.Q(email__isnull=False),
                name="accounts_user_phone_or_email",
                violation_error_message=_("Enter a phone number or an e-mail address."),
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message=_("A user with this e-mail address already exists."),
            ),
        ]

    def __str__(self):
        return self.get_full_name() or str(self.email or self.phone)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def _normalize_identifiers(self):
        self.email = normalize_email(self.email)
        if not self.phone:
            self.phone = None

    def clean(self):
        super().clean()
        self._normalize_identifiers()
        if not self.email and not self.phone:
            raise ValidationError(_("Enter a phone number or an e-mail address."))

    def save(self, *args, **kwargs):
        self._normalize_identifiers()
        super().save(*args, **kwargs)


class OtpChannel(models.TextChoices):
    WHATSAPP = "whatsapp", _("WhatsApp")
    SMS = "sms", _("SMS")
    EMAIL = "email", _("E-mail")
    CONSOLE = "console", _("Console (development)")


class OtpChallenge(BaseModel):
    """A one-time code sent to a phone number or an e-mail address.

    The code itself is never stored: only an HMAC of it. Lookups by destination use
    `destination_hash`, so rate limits do not need to scan personal data.
    """

    class DestinationKind(models.TextChoices):
        PHONE = "phone", _("Phone")
        EMAIL = "email", _("E-mail")

    class Purpose(models.TextChoices):
        SIGN_IN = "sign_in", _("Sign-up or sign-in")
        CHANGE_CONTACT = "change_contact", _("New number or e-mail")

    destination_kind = models.CharField(
        _("destination type"), max_length=8, choices=DestinationKind.choices
    )
    purpose = models.CharField(
        _("purpose"), max_length=16, choices=Purpose.choices, default=Purpose.SIGN_IN
    )
    # Set for a change of number or e-mail: the account asking for it.
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="otp_challenges",
        verbose_name=_("account"),
    )
    destination = models.CharField(_("destination"), max_length=254)
    destination_hash = models.CharField(max_length=64, db_index=True, editable=False)
    country_code = models.CharField(_("country"), max_length=2, blank=True)
    code_hash = models.CharField(max_length=64, editable=False)
    channel = models.CharField(_("channel"), max_length=10, choices=OtpChannel.choices, blank=True)
    planned_channels = models.JSONField(_("channels to try"), default=list, blank=True)
    # The code waits encrypted until the background task sends it, then is erased.
    code_encrypted = models.TextField(blank=True, editable=False)
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    delivery_failed_at = models.DateTimeField(_("delivery failed at"), null=True, blank=True)
    expires_at = models.DateTimeField(_("expires at"))
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    max_attempts = models.PositiveSmallIntegerField(_("maximum attempts"))
    verified_at = models.DateTimeField(_("verified at"), null=True, blank=True)
    ip_hash = models.CharField(max_length=64, db_index=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("one-time code")
        verbose_name_plural = _("one-time codes")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_destination_kind_display()} {self.created_at:%Y-%m-%d %H:%M}"


class LoginEvent(BaseModel):
    """Sign-in journal, successes and failures, shown in the admin."""

    class Method(models.TextChoices):
        OTP = "otp", _("One-time code")
        PASSWORD = "password", _("Password")

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_events",
        verbose_name=_("user"),
    )
    method = models.CharField(_("method"), max_length=10, choices=Method.choices)
    channel = models.CharField(_("channel"), max_length=10, choices=OtpChannel.choices, blank=True)
    success = models.BooleanField(_("success"))
    failure_reason = models.CharField(_("reason"), max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("device"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("sign-in")
        verbose_name_plural = _("sign-in journal")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user or '-'} {self.created_at:%Y-%m-%d %H:%M}"


class GuestIdentity(BaseModel):
    """A visitor without an account who left a first name and a phone number (e.g. to book).

    When she creates an account, the identity is attached to it, so nothing is lost.
    """

    first_name = models.CharField(_("first name"), max_length=150)
    phone = PhoneNumberField(_("phone number"))
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guest_identities",
        verbose_name=_("account"),
    )
    converted_at = models.DateTimeField(_("converted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("guest")
        verbose_name_plural = _("guests")
        ordering = ["-created_at"]

    def __str__(self):
        return self.first_name
