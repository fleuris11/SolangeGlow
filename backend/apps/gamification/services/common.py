"""Shared bits of the games: settings, switches, the day of a person, her Glow profile."""

from __future__ import annotations

import datetime
import secrets
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.selectors import get_setting, is_feature_enabled

from .. import errors
from ..models import GlowProfile

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def setting(key: str, default, country=None):
    return get_setting(key, country=country, default=default)


def country_of(user):
    return user.country if user is not None and getattr(user, "country_id", None) else None


def country_code(user) -> str:
    country = country_of(user)
    return country.code if country else ""


def games_on(user) -> bool:
    return is_feature_enabled("games", country=country_of(user))


def require_games(user) -> None:
    if not games_on(user):
        raise errors.GamesUnavailable()


def zone_of(user) -> ZoneInfo:
    country = country_of(user)
    return ZoneInfo(country.timezone if country else settings.TIME_ZONE)


def local_now(user, now: datetime.datetime | None = None) -> datetime.datetime:
    return (now or timezone.now()).astimezone(zone_of(user))


def today(user, now: datetime.datetime | None = None) -> datetime.date:
    """The day of the person, in the time zone of her country (Cotonou or Paris)."""
    return local_now(user, now).date()


def new_code(length: int = 8) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def profile_of(user) -> GlowProfile:
    """Her Glow profile, created the first time (with a personal referral code)."""
    found = GlowProfile.objects.filter(user=user).first()
    while found is None:
        try:
            with transaction.atomic():
                found = GlowProfile.objects.create(user=user, referral_code=new_code())
        except IntegrityError:
            found = GlowProfile.objects.filter(user=user).first()
    return found


def locked_profile(user) -> GlowProfile:
    profile_of(user)
    return GlowProfile.objects.select_for_update().get(user=user)
