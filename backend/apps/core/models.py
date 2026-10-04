import json
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .choices import Role
from .money import CURRENCY_EXPONENTS


class BaseModel(models.Model):
    """Common base for every model: UUID primary key and timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class Currency(BaseModel):
    code = models.CharField(
        _("code"),
        max_length=3,
        unique=True,
        validators=[RegexValidator(r"^[A-Z]{3}$", _("Use a 3-letter ISO 4217 code."))],
        help_text=_("ISO 4217 code, e.g. XOF or EUR."),
    )
    name = models.CharField(_("name"), max_length=64)
    symbol = models.CharField(_("symbol"), max_length=8)
    decimal_places = models.PositiveSmallIntegerField(
        _("decimal places"),
        help_text=_("Number of decimals of the currency: 0 for XOF, 2 for EUR."),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("currency")
        verbose_name_plural = _("currencies")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.symbol})"

    def clean(self):
        expected = CURRENCY_EXPONENTS.get(self.code)
        if expected is not None and self.decimal_places != expected:
            raise ValidationError(
                {"decimal_places": _("This currency has %(n)s decimal places.") % {"n": expected}}
            )


class Country(BaseModel):
    code = models.CharField(
        _("code"),
        max_length=2,
        unique=True,
        validators=[RegexValidator(r"^[A-Z]{2}$", _("Use a 2-letter ISO 3166 code."))],
        help_text=_("ISO 3166-1 alpha-2 code, e.g. BJ or FR."),
    )
    name = models.CharField(_("name"), max_length=100)
    phone_prefix = models.CharField(
        _("phone prefix"),
        max_length=6,
        validators=[RegexValidator(r"^\+\d{1,4}$", _("Use the format +229."))],
    )
    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="countries",
        verbose_name=_("default currency"),
    )
    default_language = models.CharField(
        _("default language"),
        max_length=8,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    timezone = models.CharField(_("time zone"), max_length=64, default="Europe/Paris")
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("country")
        verbose_name_plural = _("countries")
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class PlatformSetting(BaseModel):
    """A business parameter editable in the admin, optionally overridden per country.

    Read it with `apps.core.selectors.get_setting(key, country=...)`, never directly.
    """

    class ValueType(models.TextChoices):
        STRING = "string", _("Text")
        INTEGER = "integer", _("Whole number")
        DECIMAL = "decimal", _("Decimal number")
        BOOLEAN = "boolean", _("Yes / no")
        JSON = "json", _("JSON")

    key = models.CharField(
        _("key"),
        max_length=100,
        db_index=True,
        validators=[
            RegexValidator(
                r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$",
                _("Use lowercase words separated by dots, e.g. escrow.ship_deadline_days."),
            )
        ],
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="settings",
        verbose_name=_("country"),
        help_text=_("Leave empty for the default value used in every country."),
    )
    value_type = models.CharField(
        _("type"), max_length=16, choices=ValueType.choices, default=ValueType.STRING
    )
    value = models.TextField(
        _("value"),
        help_text=_("Booleans: true or false. Decimals use a dot: 12.5."),
    )
    description = models.TextField(_("description"), blank=True)

    class Meta:
        verbose_name = _("platform setting")
        verbose_name_plural = _("platform settings")
        ordering = ["key", "country__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "country"],
                name="core_platformsetting_unique_key_country",
                nulls_distinct=False,
            )
        ]

    def __str__(self):
        scope = self.country.code if self.country_id else _("all countries")
        return f"{self.key} ({scope})"

    @property
    def typed_value(self):
        return parse_setting_value(self.value_type, self.value)

    def clean(self):
        try:
            parse_setting_value(self.value_type, self.value)
        except ValueError as exc:
            raise ValidationError({"value": str(exc)}) from exc


def parse_setting_value(value_type: str, raw: str):
    """Convert the stored text into a Python value. Raises ValueError when invalid."""
    T = PlatformSetting.ValueType
    raw = raw.strip()
    if value_type == T.STRING:
        return raw
    if value_type == T.INTEGER:
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(_("Enter a whole number.")) from exc
    if value_type == T.DECIMAL:
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(_("Enter a decimal number, e.g. 12.5.")) from exc
    if value_type == T.BOOLEAN:
        lowered = raw.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        raise ValueError(_("Enter true or false."))
    if value_type == T.JSON:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(_("Enter valid JSON.")) from exc
    raise ValueError(_("Unknown type."))


class FeatureFlag(BaseModel):
    """Turns a module on or off without redeploying, per country and per role."""

    key = models.SlugField(_("key"), max_length=100, unique=True)
    name = models.CharField(_("name"), max_length=150)
    description = models.TextField(_("description"), blank=True)
    is_enabled = models.BooleanField(_("enabled"), default=False)
    countries = models.ManyToManyField(
        Country,
        blank=True,
        related_name="feature_flags",
        verbose_name=_("countries"),
        help_text=_("Leave empty to enable in every country."),
    )
    roles = ArrayField(
        models.CharField(max_length=16, choices=Role.choices),
        blank=True,
        default=list,
        verbose_name=_("roles"),
        help_text=_("Leave empty to enable for every role."),
    )

    class Meta:
        verbose_name = _("feature flag")
        verbose_name_plural = _("feature flags")
        ordering = ["key"]

    def __str__(self):
        return self.name
