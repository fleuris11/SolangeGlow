"""Shared bits of the gifts: settings, euros and FCFA, the platform as seller, links."""

from __future__ import annotations

import math
import secrets
from decimal import Decimal

import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.core.models import Country
from apps.core.money import Money
from apps.core.selectors import get_setting, is_feature_enabled

from ..models import Gift

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SOURCE = "gift"  # the payment in euros


def setting(key: str, default, country=None):
    return get_setting(key, country=country, default=default)


def rate() -> Decimal:
    """The fixed rate of the euro in FCFA (655.957 since 1999)."""
    return Decimal(str(setting("gifts.eur_xof_rate", "655.957")))


def eur_for(xof_minor: int, eur_xof: Decimal | None = None) -> int:
    """The euros (cents) that pay at least this amount of FCFA, rounded up to the cent."""
    eur_xof = eur_xof or rate()
    return math.ceil(Decimal(xof_minor) * 100 / eur_xof)


def xof_for(eur_cents: int, eur_xof: Decimal | None = None) -> int:
    """The FCFA given for euros (cents), rounded down to the franc."""
    eur_xof = eur_xof or rate()
    return math.floor(Decimal(eur_cents) * eur_xof / 100)


def card_limits() -> tuple[int, int]:
    low, high = setting("gifts.card_limits_eur", [1_000, 50_000])
    return int(low), int(high)


def countries() -> list[str]:
    """Where gifts are received and used (FCFA)."""
    return list(setting("gifts.recipient_countries", ["BJ"]) or [])


def enabled(user) -> bool:
    country = user.country if getattr(user, "country_id", None) else None
    return is_feature_enabled("gifts", country=country)


def money(amount_minor: int, currency: str, language: str = "fr") -> str:
    return Money(amount_minor, currency).format(language or "fr")


def house_account():
    """The seller of every gift: the platform in France (created the first time)."""
    User = get_user_model()
    email = setting("gifts.house_email", "cadeaux@solangeglow.com")
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            first_name="Solange Glow Cadeaux",
            country=Country.objects.filter(code="FR").first(),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def recipient_phone(raw: str) -> str:
    """E.164 when it is a valid number of a country where gifts are received, else ""."""
    try:
        number = phonenumbers.parse(raw or "", (countries() or ["BJ"])[0])
    except phonenumbers.NumberParseException:
        return ""
    if not phonenumbers.is_valid_number(number):
        return ""
    if phonenumbers.region_code_for_number(number) not in countries():
        return ""
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(10))


def new_reference() -> str:
    return "CAD-" + "".join(secrets.choice(ALPHABET) for _ in range(7))


def link(gift: Gift, language: str | None = None) -> str:
    """The page of the gift, for the person who receives it (absolute, shareable)."""
    lang = language or gift.language or "fr"
    return f"{settings.SITE_URL.rstrip('/')}/{lang}/cadeau/{gift.token}"


def locked(gift: Gift) -> Gift:
    return Gift.objects.select_for_update(of=("self",)).get(pk=gift.pk)


def is_expired(gift: Gift) -> bool:
    return gift.expires_on < timezone.localdate()


def usable(gift: Gift) -> bool:
    return gift.status in Gift.LIVE and not is_expired(gift)


def after_commit(callback) -> None:
    transaction.on_commit(callback)
