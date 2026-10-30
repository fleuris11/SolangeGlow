"""Texts of the interface corrected in the admin, without redeploying.

- Server (Django gettext): the corrections replace the texts of the loaded catalogues as
  soon as their version changes (checked at each request by a middleware).
- App (web, next-intl): the app reads the corrections of its language from the API and
  keeps them one minute.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import trans_real

from apps.core.audit.services import record

from ..models import TranslationOverride

logger = logging.getLogger("solangeglow.backoffice")
VERSION_KEY = "i18n:overrides:version"
D = TranslationOverride.Domain
_applied = {"version": None}


def version() -> int:
    value = cache.get(VERSION_KEY)
    if value is None:
        value = 1
        cache.set(VERSION_KEY, value, None)
    return int(value)


def changed() -> None:
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, None)
    for language, _name in settings.LANGUAGES:
        cache.delete(f"i18n:web:{language}")


def save(*, domain: str, language: str, key: str, text: str, actor) -> TranslationOverride | None:
    """Saves a correction; an empty text goes back to the original."""
    key = key.strip()
    if not text.strip():
        TranslationOverride.objects.filter(domain=domain, language=language, key=key).delete()
        found = None
    else:
        found, _ = TranslationOverride.objects.update_or_create(
            domain=domain,
            language=language,
            key=key,
            defaults={"text": text, "updated_by": actor},
        )
    record(
        "backoffice.translation_changed",
        found,
        actor=actor,
        metadata={"domain": domain, "language": language, "key": key[:200]},
    )
    changed()
    return found


def apply_server(force: bool = False) -> None:
    """Loads the catalogues again and puts the corrections of the server in them."""
    current = version()
    if not force and _applied["version"] == current:
        return
    trans_real._translations = {}
    trans_real._default = None
    for row in TranslationOverride.objects.filter(domain=D.SERVER):
        try:
            catalog = trans_real.translation(row.language)._catalog
            catalog[row.key] = row.text
        except Exception:  # a catalogue that cannot load must not break the request
            logger.exception("Translation override %s not applied", row.pk)
    _applied["version"] = current


class TranslationOverrideMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        apply_server()
        return self.get_response(request)


def web_overrides(language: str) -> dict:
    key = f"i18n:web:{language}"
    found = cache.get(key)
    if found is None:
        found = dict(
            TranslationOverride.objects.filter(domain=D.WEB, language=language).values_list(
                "key", "text"
            )
        )
        cache.set(key, found, 3600)
    return found


# --- Search by key or by text -----------------------------------------------------------------


def _flatten(prefix: str, value, out: dict) -> None:
    if isinstance(value, dict):
        for name, child in value.items():
            _flatten(f"{prefix}.{name}" if prefix else name, child, out)
    else:
        out[prefix] = str(value)


def web_catalog(language: str) -> dict:
    """The texts of the app in a language (read from the app itself, kept 10 minutes)."""
    key = f"i18n:webcatalog:{language}"
    found = cache.get(key)
    if found is not None:
        return found
    url = f"{settings.WEB_INTERNAL_URL.rstrip('/')}/i18n-catalog/{language}"
    found = {}
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - our own app
            _flatten("", json.loads(response.read().decode()), found)
    except (OSError, ValueError):
        logger.warning("Web catalogue %s not reachable", language)
        return {}
    cache.set(key, found, 600)
    return found


def server_catalog(language: str) -> dict:
    catalog = trans_real.translation(language)._catalog
    return {key: str(value) for key, value in catalog.items() if isinstance(key, str) and key}


def search(query: str, language: str, *, limit: int = 60) -> list[dict]:
    """Texts whose key or text contains the words, with their correction if any."""
    words = (query or "").strip().lower()
    if len(words) < 2:
        return []
    overrides = {
        (row.domain, row.key): row.text
        for row in TranslationOverride.objects.filter(language=language)
    }
    rows = []
    for domain, catalog in ((D.WEB, web_catalog(language)), (D.SERVER, server_catalog(language))):
        for key, text in catalog.items():
            corrected = overrides.get((domain, key))
            if (
                words in key.lower()
                or words in text.lower()
                or (corrected and words in corrected.lower())
            ):
                rows.append(
                    {"domain": domain, "key": key, "text": text, "override": corrected or ""}
                )
                if len(rows) >= limit:
                    return rows
    return rows
