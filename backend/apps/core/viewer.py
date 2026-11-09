"""The country whose content a person sees: one rule for the whole platform.

1. The country asked in the address (``?country=BJ``): a screen that compares countries.
2. The one her device sends (``X-SG-Country``): chosen by her in the app, or found from her
   time zone on her first visit. ``*`` means she chose to see every country.
3. The country of her account.
4. None: every country.

Feed, search, lives, courses and places all ask here, so they always agree.
"""

from __future__ import annotations

from apps.core.models import Country

HEADER = "HTTP_X_SG_COUNTRY"
EVERYWHERE = "*"
_CACHE = "_sg_viewer_country"


def _active(code: str) -> Country | None:
    code = (code or "").strip().upper()[:2]
    if len(code) != 2:
        return None
    return Country.objects.filter(code=code, is_active=True).first()


def viewer_country(request, asked: str = "") -> Country | None:
    if asked:
        return _active(asked)
    if hasattr(request, _CACHE):
        return getattr(request, _CACHE)
    sent = (request.META.get(HEADER) or "").strip()
    if sent == EVERYWHERE:
        country = None
    elif sent:
        country = _active(sent)
    else:
        user = getattr(request, "user", None)
        country = (
            user.country if user is not None and user.is_authenticated and user.country_id else None
        )
    setattr(request, _CACHE, country)
    return country


def viewer_country_key(request) -> str:
    """What the answer depends on, for the caches shared by visitors."""
    return (request.META.get(HEADER) or "").strip()[:2].upper()
