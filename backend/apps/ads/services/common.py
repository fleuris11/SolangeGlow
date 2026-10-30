"""Shared bits of the ads: settings, the person who sees an ad, the cache version."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from django.core.cache import cache
from django.utils import timezone

from apps.accounts.selectors import is_minor
from apps.core.selectors import get_setting, is_feature_enabled

from ..models import Placement

VERSION_KEY = "ads:version"
DEFAULT_MAX_PER_SCREEN = {
    Placement.HOME_BANNER: 1,
    Placement.FEED: 2,
    Placement.PRODUCT: 1,
    Placement.SEARCH: 1,
    Placement.SPLASH: 1,
}
DEFAULT_FILLER = {
    Placement.HOME_BANNER: "house",
    Placement.FEED: "house",
    Placement.PRODUCT: "house",
    Placement.SEARCH: "none",
    Placement.SPLASH: "none",
}


def setting(key: str, default, country=None):
    return get_setting(key, country=country, default=default)


def version() -> int:
    value = cache.get(VERSION_KEY)
    if value is None:
        value = 1
        cache.set(VERSION_KEY, value, None)
    return int(value)


def changed() -> None:
    """A campaign, a creative or a boost changed: the lists of ads are built again."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, None)


def max_per_screen(placement: str) -> int:
    values = setting("ads.max_per_screen", DEFAULT_MAX_PER_SCREEN) or {}
    return max(0, int(values.get(placement, 1)))


def filler(placement: str) -> str:
    values = setting("ads.filler", DEFAULT_FILLER) or {}
    found = values.get(placement, "none")
    return found if found in ("house", "adsense", "none") else "none"


@dataclass(frozen=True)
class Audience:
    """Who sees the ad: a signed-in person, or a visitor known by a random cookie."""

    viewer: str  # "u:<id>" or "v:<hash of the visitor cookie>", "" when unknown
    user_id: object = None
    country: str = ""
    city: str = ""
    language: str = "fr"
    roles: frozenset = field(default_factory=frozenset)
    trades: frozenset = field(default_factory=frozenset)
    minor: bool = False


def audience_of(
    user, *, visitor: str = "", country: str = "", city: str = "", language: str = "fr"
):
    if user is not None and getattr(user, "is_authenticated", False):
        roles = set(user.roles or [])
        trades = set()
        pro = getattr(user, "pro_profile", None)  # None when she has no showcase
        if pro is not None:
            roles.add("pro")
            trades = set(pro.trades.values_list("key", flat=True))
        roles.add("client")
        return Audience(
            viewer=f"u:{user.pk}",
            user_id=user.pk,
            country=user.country.code if user.country_id else country,
            city=(user.city or city or "").strip(),
            language=user.preferred_language or language,
            roles=frozenset(roles),
            trades=frozenset(trades),
            minor=is_minor(user),
        )
    key = hashlib.sha256(visitor.encode()).hexdigest()[:24] if visitor else ""
    return Audience(
        viewer=f"v:{key}" if key else "",
        country=country,
        city=(city or "").strip(),
        language=language or "fr",
        roles=frozenset({"client"}),
    )


def ads_on(audience: Audience) -> bool:
    if not is_feature_enabled("ads", country=audience.country or None):
        return False
    return not (audience.minor and setting("ads.hide_for_minors", True))


def today():
    return timezone.localdate()
