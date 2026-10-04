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

    # OTP sign-in (WhatsApp, SMS, e-mail) will plug in here: a dedicated model in this
    # app storing hashed one-time codes, plus `phone_verified_at` / `email_verified_at`.

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
