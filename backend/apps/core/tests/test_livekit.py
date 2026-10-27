"""LiveKit: tokens hold exactly what a person may do, server calls, signed webhooks."""

import json

import httpx
import jwt
import pytest
from django.urls import reverse

from apps.core.providers import livekit
from apps.core.providers.base import ProviderError, ProviderNotConfigured

SECRET = "a-long-enough-secret-for-the-tests-0123456789"


def make(**kwargs):
    return livekit.LiveKit("ws://localhost:7880", "http://web:7880", "devkey", SECRET, **kwargs)


def claims(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def test_livekit_needs_its_keys(settings):
    settings.LIVEKIT_URL = ""
    with pytest.raises(ProviderNotConfigured):
        livekit.client()
    assert not livekit.available()
    settings.LIVEKIT_URL = "ws://localhost:7880"
    settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET = "devkey", SECRET
    settings.LIVEKIT_API_URL = ""
    found = livekit.client()
    assert found.api_url == "http://localhost:7880" and livekit.available()


def test_a_viewer_only_watches_a_host_films_and_speaks():
    viewer = claims(make().token(room="live-1", identity="u1", name="Awa", ttl=600))
    assert viewer["iss"] == "devkey" and viewer["sub"] == "u1"
    grant = viewer["video"]
    assert grant["room"] == "live-1" and grant["roomJoin"] and grant["canSubscribe"]
    assert grant["canPublish"] is False and grant["canPublishSources"] == []
    assert grant["canPublishData"] is False
    assert viewer["exp"] - viewer["nbf"] == 605

    host = claims(make().token(room="live-1", identity="u2", sources=["camera", "microphone"]))
    assert host["video"]["canPublish"] and host["video"]["canPublishSources"] == [
        "camera",
        "microphone",
    ]
    assert "roomAdmin" not in host["video"]  # nobody drives the room from her phone


def test_server_calls_carry_an_admin_token(monkeypatch):
    seen = []

    def post(url, json, headers, timeout):
        seen.append((url, json, claims(headers["Authorization"].removeprefix("Bearer "))))
        body = b'{"egress_id": "EG_1"}' if "Egress" in url else b""
        return httpx.Response(200, content=body)

    monkeypatch.setattr(httpx, "post", post)
    lk = make()
    lk.create_room("live-1", max_participants=305)
    lk.set_sources("live-1", "u1", ["microphone"])
    lk.send("live-1", {"type": "questions"})
    assert lk.record("live-1", "u2", "private/originals/video/x/original.mp4") == "EG_1"
    lk.stop_recording("EG_1")
    lk.delete_room("live-1")
    urls = [url.rsplit("/", 1)[-1] for url, _body, _claims in seen]
    assert urls == [
        "CreateRoom",
        "UpdateParticipant",
        "SendData",
        "StartParticipantEgress",
        "StopEgress",
        "DeleteRoom",
    ]
    assert seen[0][2]["video"] == {"roomCreate": True}
    assert seen[1][1]["permission"]["can_publish_sources"] == ["MICROPHONE"]
    assert seen[1][2]["video"] == {"roomAdmin": True, "room": "live-1"}
    assert json.loads(__import__("base64").b64decode(seen[2][1]["data"])) == {"type": "questions"}
    assert seen[3][2]["video"] == {"roomRecord": True}


def test_server_errors_become_provider_errors(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(500))
    with pytest.raises(ProviderError):
        make().delete_room("live-1")

    def down(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", down)
    with pytest.raises(ProviderError):
        make().delete_room("live-1")


def test_webhooks_are_checked(fake_livekit):
    body = json.dumps({"event": "room_finished", "room": {"name": "nobody-1"}}).encode()
    assert fake_livekit.verify(body, fake_livekit.sign(body))["event"] == "room_finished"
    with pytest.raises(ValueError):
        fake_livekit.verify(body + b" ", fake_livekit.sign(body))
    with pytest.raises(ValueError):
        fake_livekit.verify(body, "not-a-token")


@pytest.mark.django_db
def test_the_webhook_endpoint_refuses_unsigned_events(client, fake_livekit):
    handled = []
    livekit.on_webhook("test-", lambda name, event: handled.append(name))
    body = json.dumps({"event": "participant_joined", "room": {"name": "test-1"}}).encode()
    url = reverse("v1:livekit-webhook")
    refused = client.post(url, body, content_type="application/webhook+json")
    assert refused.status_code == 401 and not handled
    accepted = client.post(
        url,
        body,
        content_type="application/webhook+json",
        HTTP_AUTHORIZATION=fake_livekit.sign(body),
    )
    assert accepted.status_code == 200 and handled == ["participant_joined"]
    egress = {"event": "egress_ended", "egressInfo": {"roomName": "elsewhere"}}
    assert livekit.dispatch(egress) is False
