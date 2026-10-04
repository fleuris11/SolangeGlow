"""Read helpers for platform-wide configuration (settings and feature flags).

Both are cached (Redis in dev/prod) and invalidated on every save or delete.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.conf import settings
from django.core.cache import cache

from .models import Country, FeatureFlag, PlatformSetting

GLOBAL_SCOPE = "*"
_MISSING = object()


class SettingNotFound(KeyError):
    """No value exists for this key (neither for the country nor globally)."""


def _country_code(country: Country | str | None) -> str | None:
    if country is None:
        return None
    if isinstance(country, Country):
        return country.code
    return country.upper()


def setting_cache_key(key: str) -> str:
    return f"core:setting:{key}"


def flag_cache_key(key: str) -> str:
    return f"core:flag:{key}"


def _load_setting_values(key: str) -> dict[str, object]:
    """All values of a key, indexed by country code ("*" for the default)."""
    cache_key = setting_cache_key(key)
    values = cache.get(cache_key)
    if values is None:
        values = {
            (s.country.code if s.country_id else GLOBAL_SCOPE): s.typed_value
            for s in PlatformSetting.objects.filter(key=key).select_related("country")
        }
        cache.set(cache_key, values, settings.PLATFORM_SETTINGS_CACHE_TIMEOUT)
    return values


def get_setting(key: str, country: Country | str | None = None, default=_MISSING):
    """Return the value of a business parameter.

    The country-specific value wins over the default one. Raises `SettingNotFound`
    when nothing is configured and no `default` is given.
    """
    values = _load_setting_values(key)
    code = _country_code(country)
    if code and code in values:
        return values[code]
    if GLOBAL_SCOPE in values:
        return values[GLOBAL_SCOPE]
    if default is not _MISSING:
        return default
    raise SettingNotFound(key)


def _load_flag(key: str) -> dict | None:
    cache_key = flag_cache_key(key)
    data = cache.get(cache_key, _MISSING)
    if data is _MISSING:
        flag = FeatureFlag.objects.filter(key=key).prefetch_related("countries").first()
        data = (
            None
            if flag is None
            else {
                "enabled": flag.is_enabled,
                "countries": {c.code for c in flag.countries.all()},
                "roles": set(flag.roles),
            }
        )
        cache.set(cache_key, data, settings.PLATFORM_SETTINGS_CACHE_TIMEOUT)
    return data


def is_feature_enabled(
    key: str,
    *,
    country: Country | str | None = None,
    roles: Iterable[str] | None = None,
) -> bool:
    """True when the flag exists, is on, and matches the country and one of the roles.

    An empty country or role list on the flag means "everyone".
    """
    data = _load_flag(key)
    if not data or not data["enabled"]:
        return False
    code = _country_code(country)
    if data["countries"] and code not in data["countries"]:
        return False
    return not data["roles"] or bool(data["roles"].intersection(roles or ()))
