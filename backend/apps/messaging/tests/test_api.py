import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.messaging import services

from .factories import adult, pro, upload

pytestmark = pytest.mark.django_db
HEADERS = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_visitors_cannot_use_the_messaging(api_client):
    assert api_client.get(reverse("v1:conversations")).status_code == 401


def test_write_to_a_pro_then_list_and_read():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    client = signed_in(awa)
    started = client.post(
        reverse("v1:conversations"), {"person_id": str(aicha.pk)}, format="json", **HEADERS
    )
    assert started.status_code == 201
    conversation = started.json()
    assert conversation["people"][0]["name"] == "Aïcha Tresses"
    assert conversation["people"][0]["is_pro"] is True

    url = reverse("v1:conversation-messages", args=[conversation["id"]])
    sent = client.post(
        url, {"text": "Bonjour", "client_id": str(uuid.uuid4())}, format="json", **HEADERS
    )
    assert sent.status_code == 201 and sent.json()["state"] == "visible"

    pro_client = signed_in(aicha)
    inbox = pro_client.get(reverse("v1:conversations")).json()["results"]
    assert inbox[0]["unread"] == 1 and inbox[0]["last_message"]["text"] == "Bonjour"
    assert pro_client.get(reverse("v1:messaging-unread")).json() == {"count": 1, "requests": 0}

    page = pro_client.get(url).json()
    assert [m["text"] for m in page["results"]] == ["Bonjour"]
    assert (
        pro_client.post(
            reverse("v1:conversation-read", args=[conversation["id"]]), **HEADERS
        ).status_code
        == 204
    )
    after = client.get(reverse("v1:conversation", args=[conversation["id"]])).json()
    assert after["receipts"]["read_up_to"] is not None


def test_messages_come_in_pages_oldest_first():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    for number in range(35):
        services.send(awa, conversation.pk, text=f"Message {number}")
    url = reverse("v1:conversation-messages", args=[conversation.pk])
    first = signed_in(aicha).get(url).json()
    assert first["results"][-1]["text"] == "Message 34" and len(first["results"]) == 30
    older = signed_in(aicha).get(url, {"before": first["next"]}).json()
    assert older["results"][0]["text"] == "Message 0" and older["next"] is None


def test_clear_refusals():
    awa, ines = adult("Awa"), adult("Inès")
    refused = signed_in(awa).post(
        reverse("v1:conversations"), {"person_id": str(ines.pk)}, format="json", **HEADERS
    )
    assert refused.status_code == 403 and refused.json()["code"] == "mutual_follow_needed"

    other = services.start_direct(adult("Zoé"), pro("Gloria Nails"))
    hidden = signed_in(awa).get(reverse("v1:conversation-messages", args=[other.pk]))
    assert hidden.status_code == 404


def test_message_requests_box_accept_and_decline():
    aicha, awa = pro("Aïcha Tresses"), adult("Awa")
    conversation = services.start_direct(aicha, awa)
    services.send(aicha, conversation.pk, text="Bonjour, promo ce week-end")
    client = signed_in(awa)
    assert client.get(reverse("v1:conversations")).json()["results"] == []
    requests = client.get(reverse("v1:conversations"), {"box": "requests"}).json()["results"]
    assert requests[0]["status"] == "requested"
    accepted = client.post(reverse("v1:conversation-accept", args=[conversation.pk]), **HEADERS)
    assert accepted.json()["status"] == "active"
    assert len(client.get(reverse("v1:conversations")).json()["results"]) == 1


def test_photo_share_delete_and_report_endpoints():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    url = reverse("v1:conversation-messages", args=[conversation.pk])
    client = signed_in(awa)
    photo = client.post(url, {"media_id": str(upload(awa).pk)}, format="json", **HEADERS).json()
    assert photo["kind"] == "photo" and photo["media"]["urls"]["medium"]

    risky = services.send(aicha, conversation.pk, text="Paie par Western Union")
    seen = client.get(url).json()["results"][-1]
    assert seen["fraud_labels"] == ["keyword"]
    details = client.get(reverse("v1:conversation", args=[conversation.pk])).json()
    assert details["payment_warning"] is True

    reported = client.post(
        reverse("v1:message-report", args=[risky.pk]), {"reason": "scam"}, format="json", **HEADERS
    )
    assert reported.status_code == 201
    assert client.delete(reverse("v1:message", args=[photo["id"]]), **HEADERS).status_code == 204
    assert client.get(url).json()["results"][0]["state"] == "deleted"


def test_quick_replies_and_away_message_endpoints():
    aicha = pro("Aïcha Tresses")
    client = signed_in(aicha)
    saved = client.put(
        reverse("v1:quick-replies"),
        {"texts": ["Oui c'est disponible", "Voici mes tarifs"]},
        format="json",
        **HEADERS,
    )
    assert saved.json()["texts"] == ["Oui c'est disponible", "Voici mes tarifs"]
    away = client.put(
        reverse("v1:away-message"),
        {"enabled": True, "text": "De retour lundi"},
        format="json",
        **HEADERS,
    )
    assert away.json() == {"enabled": True, "text": "De retour lundi"}
    refused = signed_in(adult("Awa")).put(
        reverse("v1:quick-replies"), {"texts": ["Oui"]}, format="json", **HEADERS
    )
    assert refused.status_code == 403
