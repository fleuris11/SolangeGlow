"""LiveKit (ADR-013): audio and video calls and lives, without anybody's phone number.

The backend gives each person a short-lived token for one room, with exactly what she may
do (speak, film, only watch). It also drives the rooms through the server API (create,
close, give or take the floor, send an event to everybody, record the host) and receives
the signed webhooks of the server (who came in, who left, a recording is ready).

Development: the "livekit" service of docker compose (docker/livekit/livekit.yaml).
Tests: `use_fake()` (FakeLiveKit records every call, tokens stay real).
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import logging
from collections.abc import Callable, Iterable

import httpx
import jwt
from django.conf import settings
from django.utils import timezone

from .base import ProviderError, ProviderNotConfigured

logger = logging.getLogger("solangeglow.livekit")

CAMERA = "camera"
MICROPHONE = "microphone"
_SOURCE_ENUM = {CAMERA: "CAMERA", MICROPHONE: "MICROPHONE"}


class LiveKit:
    name = "livekit"

    def __init__(self, url: str, api_url: str, api_key: str, api_secret: str, *, egress=False):
        if not (url and api_key and api_secret):
            raise ProviderNotConfigured("LiveKit")
        self.url = url
        self.api_url = (api_url or url.replace("ws", "http", 1)).rstrip("/")
        self.api_key, self.api_secret = api_key, api_secret
        self.egress = egress

    # --- Tokens --------------------------------------------------------------------------

    def _jwt(self, claims: dict, ttl: int) -> str:
        now = timezone.now()
        body = {
            "iss": self.api_key,
            "nbf": int(now.timestamp()) - 5,
            "exp": int((now + datetime.timedelta(seconds=ttl)).timestamp()),
            **claims,
        }
        return jwt.encode(body, self.api_secret, algorithm="HS256")

    def token(
        self,
        *,
        room: str,
        identity: str,
        name: str = "",
        ttl: int = 600,
        sources: Iterable[str] = (),
        metadata: str = "",
    ) -> str:
        """Joins one room. `sources` (camera, microphone) are what she may send; empty:
        she only watches and listens. Nobody sends free data: events go through the API."""
        sources = list(sources)
        grant = {
            "room": room,
            "roomJoin": True,
            "canSubscribe": True,
            "canPublish": bool(sources),
            "canPublishData": False,
            "canPublishSources": sources,
            "canUpdateOwnMetadata": False,
        }
        claims = {"sub": identity, "name": name[:60], "video": grant}
        if metadata:
            claims["metadata"] = metadata
        return self._jwt(claims, ttl)

    # --- Server API (Twirp, JSON) -----------------------------------------------------------

    def _call(self, service: str, method: str, body: dict, grant: dict) -> dict:
        token = self._jwt({"video": grant}, 60)
        try:
            response = httpx.post(
                f"{self.api_url}/twirp/livekit.{service}/{method}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"LiveKit {method}: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"LiveKit {method}: HTTP {response.status_code}")
        return response.json() if response.content else {}

    def create_room(self, name: str, *, max_participants: int, empty_timeout: int = 300) -> None:
        self._call(
            "RoomService",
            "CreateRoom",
            {"name": name, "max_participants": max_participants, "empty_timeout": empty_timeout},
            {"roomCreate": True},
        )

    def delete_room(self, name: str) -> None:
        self._call("RoomService", "DeleteRoom", {"room": name}, {"roomCreate": True})

    def set_sources(self, room: str, identity: str, sources: Iterable[str]) -> None:
        """Gives (or takes back) the floor: what she may send, applied at once."""
        sources = list(sources)
        permission = {
            "can_subscribe": True,
            "can_publish": bool(sources),
            "can_publish_data": False,
            "can_publish_sources": [_SOURCE_ENUM[s] for s in sources],
        }
        self._call(
            "RoomService",
            "UpdateParticipant",
            {"room": room, "identity": identity, "permission": permission},
            {"roomAdmin": True, "room": room},
        )

    def send(self, room: str, event: dict) -> None:
        """An event for every device in the room (they reload what changed)."""
        data = base64.b64encode(json.dumps(event).encode()).decode()
        self._call(
            "RoomService",
            "SendData",
            {"room": room, "data": data, "kind": "RELIABLE", "topic": "sg"},
            {"roomAdmin": True, "room": room},
        )

    def record(self, room: str, identity: str, filepath: str) -> str:
        """Records one person (camera and voice) into the storage; returns the egress id."""
        answer = self._call(
            "Egress",
            "StartParticipantEgress",
            {
                "room_name": room,
                "identity": identity,
                "file_outputs": [{"file_type": "MP4", "filepath": filepath}],
            },
            {"roomRecord": True},
        )
        return answer.get("egress_id") or answer.get("egressId") or ""

    def stop_recording(self, egress_id: str) -> None:
        self._call("Egress", "StopEgress", {"egress_id": egress_id}, {"roomRecord": True})

    # --- Webhooks ---------------------------------------------------------------------------

    def verify(self, body: bytes, authorization: str) -> dict:
        """The event, once the signature and the body hash are checked (else ValueError)."""
        try:
            claims = jwt.decode(
                authorization.removeprefix("Bearer ").strip(),
                self.api_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                leeway=30,
            )
        except jwt.PyJWTError as exc:
            raise ValueError("bad signature") from exc
        digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
        if claims.get("iss") != self.api_key or claims.get("sha256") != digest:
            raise ValueError("bad signature")
        return json.loads(body)


class FakeLiveKit(LiveKit):
    """Tests: the same tokens, server calls only recorded."""

    name = "fake"

    def __init__(self, *, egress=True, fail=False):
        super().__init__(
            "ws://livekit.test", "http://livekit.test", "testkey", "x" * 40, egress=egress
        )
        self.calls: list[tuple] = []
        self.fail = fail

    def _call(self, service, method, body, grant):
        if self.fail:
            raise ProviderError(method)
        self.calls.append((method, body))
        if method == "StartParticipantEgress":
            return {"egress_id": f"EG_{len(self.calls)}"}
        return {}

    def sent(self, method: str) -> list[dict]:
        return [body for name, body in self.calls if name == method]

    def sign(self, body: bytes) -> str:
        digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
        return self._jwt({"sha256": digest}, 60)


_override: LiveKit | None = None


def use_fake(fake: LiveKit | None) -> None:
    global _override
    _override = fake


def client() -> LiveKit:
    """Raises ProviderNotConfigured until LIVEKIT_URL, _API_KEY and _API_SECRET are set."""
    if _override is not None:
        return _override
    return LiveKit(
        settings.LIVEKIT_URL,
        settings.LIVEKIT_API_URL,
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET,
        egress=settings.LIVEKIT_EGRESS,
    )


def available() -> bool:
    try:
        client()
    except ProviderNotConfigured:
        return False
    return True


# --- Webhook handlers: each module takes the rooms of its prefix ----------------------------

_handlers: dict[str, Callable[[str, dict], None]] = {}


def on_webhook(prefix: str, handler: Callable[[str, dict], None]) -> None:
    _handlers[prefix] = handler


def room_of(event: dict) -> str:
    room = (event.get("room") or {}).get("name")
    if room:
        return room
    egress = event.get("egressInfo") or event.get("egress_info") or {}
    return egress.get("roomName") or egress.get("room_name") or ""


def dispatch(event: dict) -> bool:
    room = room_of(event)
    for prefix, handler in _handlers.items():
        if room.startswith(prefix):
            handler(event.get("event", ""), event)
            return True
    return False
