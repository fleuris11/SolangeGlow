"""Broadcast of the training lives, behind an interface (ADR-012). The provider is chosen
in the environment (LIVE_PROVIDER, a class path); empty: lives are planned, students
register and wait in the room, but the video is not available yet (prompt 14)."""

from __future__ import annotations

from django.conf import settings
from django.utils.module_loading import import_string

from apps.core.providers.base import ProviderNotConfigured


class LiveProvider:
    """What a broadcast service gives: a room per live, a link to join it."""

    name = "base"

    def create_room(self, live) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def join_url(self, live, user, *, host: bool) -> str:  # pragma: no cover - interface
        raise NotImplementedError


def live_provider() -> LiveProvider:
    path = getattr(settings, "LIVE_PROVIDER", "")
    if not path:
        raise ProviderNotConfigured("live")
    return import_string(path)()
