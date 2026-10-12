"""Audio and video calls (connected later): the CallProvider interface and LiveKit.

A call happens in a room named after the conversation; each person gets a short-lived
token to join it, so nobody sees anybody's phone number. Development uses the LiveKit
server of docker compose (`docker compose --profile calls up livekit`).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Protocol

import jwt
from django.conf import settings
from django.utils import timezone

from apps.core.providers.base import ProviderNotConfigured


@dataclass(frozen=True)
class CallAccess:
    url: str
    room: str
    token: str
    expires_at: datetime.datetime


class CallProvider(Protocol):
    name: str

    def room_for(self, conversation) -> str: ...

    def access(self, conversation, user, *, video: bool) -> CallAccess: ...


class LiveKitCallProvider:
    name = "livekit"

    def __init__(self, url: str, api_key: str, api_secret: str, ttl_seconds: int = 600):
        if not (url and api_key and api_secret):
            raise ProviderNotConfigured("LiveKit")
        self.url, self.api_key, self.api_secret, self.ttl = url, api_key, api_secret, ttl_seconds

    def room_for(self, conversation) -> str:
        return f"conversation-{conversation.pk}"

    def access(self, conversation, user, *, video: bool) -> CallAccess:
        now = timezone.now()
        expires = now + datetime.timedelta(seconds=self.ttl)
        room = self.room_for(conversation)
        claims = {
            "iss": self.api_key,
            "sub": str(user.pk),
            "nbf": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "name": user.first_name or "",
            "video": {
                "room": room,
                "roomJoin": True,
                "canPublish": True,
                "canSubscribe": True,
                "canPublishSources": ["microphone", "camera"] if video else ["microphone"],
            },
        }
        token = jwt.encode(claims, self.api_secret, algorithm="HS256")
        return CallAccess(url=self.url, room=room, token=token, expires_at=expires)


def get_call_provider() -> CallProvider:
    """Raises ProviderNotConfigured until LIVEKIT_URL, _API_KEY and _API_SECRET are set."""
    return LiveKitCallProvider(
        settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET
    )
