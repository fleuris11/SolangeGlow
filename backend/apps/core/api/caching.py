"""Answers shared by every visitor who is not signed in, kept a few seconds in the cache.

Most people who open the site are visitors: the home feed, the search, a showcase, a shop or a
course are the same for all of them. Computing them once every few seconds instead of on every
request is the cheapest way to keep the site fast when many people arrive at once.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import get_language
from rest_framework.response import Response

from apps.core.selectors import get_setting
from apps.core.viewer import viewer_country_key

SETTING = "performance.visitor_cache_seconds"


def visitor_cache_seconds() -> int:
    if not settings.VISITOR_CACHE:
        return 0
    try:
        return max(0, int(get_setting(SETTING, default=60)))
    except (TypeError, ValueError):
        return 0


def visitor_cache_key(request) -> str:
    raw = f"{request.get_full_path()}|{get_language() or ''}|{viewer_country_key(request)}"
    return "visitor-answer:" + hashlib.sha256(raw.encode()).hexdigest()


# GET: same address and language, same answer for visitors, during the setting's seconds.
# Signed-in people always get a fresh answer (their own drafts, their likes, their country).
# Only answers that depend on nothing but the address may use it: never one that reads a
# cookie, the IP address or the time to the second (slots, ads that count what is shown).
# (A comment, not a docstring: the API documentation keeps the view's own description.)
class VisitorCacheMixin:
    # Plugged after authentication, permissions and rate limits (so they still apply), and
    # before the view's own get(), which most views define themselves.
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method != "GET":
            return
        seconds = visitor_cache_seconds()
        if seconds == 0 or request.user.is_authenticated:
            return
        key = visitor_cache_key(request)
        data = cache.get(key)
        if data is not None:
            self.get = lambda *args, **kwargs: Response(data)
            return
        compute = self.get

        def get_and_keep(*args, **kwargs):
            response = compute(*args, **kwargs)
            if response.status_code == 200:
                cache.set(key, response.data, seconds)
            return response

        self.get = get_and_keep
