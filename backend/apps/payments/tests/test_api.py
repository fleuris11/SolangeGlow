"""The payment API, from both sides, the courier link and the webhook endpoint."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.messaging.tests.factories import adult
from apps.payments.models import Payment
from apps.payments.providers import EventKind
from apps.payments.providers.fake import signed_event

from .factories import code_of, paid, payment, picture, shipped

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_the_whole_flow_through_the_api():
    from .factories import seller

    aicha = seller()
    awa = adult("Awa")
    client = signed_in(awa)
    demo = client.post(
        reverse("v1:dev-payments"),
        {
            "seller_slug": aicha.pro_profile.slug,
            "items_minor": 10_000,
            "delivery_minor": 1_000,
            "description": "Perruque",
        },
        format="json",
        **H,
    )
    assert demo.status_code == 201
    data = demo.json()
    assert data["total_minor"] == 11_330 and data["can"]["pay"] and data["checkout_url"]
    assert data["commission_minor"] is None  # the client never sees the commission
    pid = data["id"]

    paid_now = client.post(
        reverse("v1:payment-test-outcome", args=[pid]), {"outcome": "succeeded"}, format="json", **H
    ).json()
    assert paid_now["status"] == "held" and len(paid_now["receipt_code"]) == 6
    code = paid_now["receipt_code"]

    shop = signed_in(aicha)
    seen = shop.get(reverse("v1:payment", args=[pid])).json()
    assert seen["receipt_code"] is None and seen["seller_net_minor"] == 11_000
    assert seen["can"]["ship"] and seen["code_attempts_left"] == 5
    assert shop.get(reverse("v1:payments"), {"role": "seller"}).json()["results"][0]["id"] == pid
    assert client.get(reverse("v1:payments")).json()["results"][0]["id"] == pid

    shipped_now = shop.post(
        reverse("v1:payment-ship", args=[pid]), {"carrier": "Gozem"}, format="json", **H
    ).json()
    assert shipped_now["status"] == "shipped"
    wrong = shop.post(reverse("v1:payment-confirm", args=[pid]), {"code": "000000"}, **H)
    assert wrong.status_code == 400 and wrong.json()["code"] == "wrong_code"
    done = shop.post(reverse("v1:payment-confirm", args=[pid]), {"code": code}, format="json", **H)
    assert done.json()["status"] == "released"

    wallet = shop.get(reverse("v1:wallet")).json()
    assert wallet["wallets"][0]["available_minor"] == 11_000
    history = shop.get(reverse("v1:wallet-history"), {"currency": "XOF"}).json()
    assert {line["account"] for line in history} == {"pending", "available"}
    method = shop.put(
        reverse("v1:payout-methods"), {"currency": "XOF", "kind": "fake"}, format="json", **H
    )
    assert method.json()["kind"] == "fake"
    assert shop.get(reverse("v1:payout-methods")).json()[0]["currency"] == "XOF"
    payout = shop.post(
        reverse("v1:payouts"), {"amount_minor": 11_000, "currency": "XOF"}, format="json", **H
    )
    assert payout.status_code == 201 and payout.json()["status"] == "paid"
    assert shop.get(reverse("v1:wallet")).json()["wallets"][0]["paid_out_minor"] == 11_000


def test_strangers_see_nothing():
    p = paid()
    stranger = signed_in(adult("Zoé"))
    assert stranger.get(reverse("v1:payment", args=[p.pk])).status_code == 404
    assert APIClient().get(reverse("v1:payment", args=[p.pk])).status_code == 401


def test_checkout_cancel_new_code_and_failed_test_payment():
    p = payment()
    client = signed_in(p.buyer)
    started = client.post(reverse("v1:payment-checkout", args=[p.pk]), **H).json()
    assert started["checkout_url"].endswith(f"/pay/test/{p.pk}")
    failed = client.post(
        reverse("v1:payment-test-outcome", args=[p.pk]), {"outcome": "failed"}, format="json", **H
    ).json()
    assert failed["status"] == "cancelled"
    again = client.post(
        reverse("v1:payment-test-outcome", args=[p.pk]), {"outcome": "succeeded"}, **H
    )
    assert again.status_code == 409

    held = paid()
    client = signed_in(held.buyer)
    assert client.post(reverse("v1:payment-new-code", args=[held.pk]), **H).status_code == 200
    cancelled = client.post(reverse("v1:payment-cancel", args=[held.pk]), **H).json()
    assert cancelled["status"] == "refunded" and cancelled["refunded_minor"] == 11_330


def test_test_outcome_only_for_the_test_provider():
    p = payment()
    Payment.objects.filter(pk=p.pk).update(provider="fedapay")
    response = signed_in(p.buyer).post(
        reverse("v1:payment-test-outcome", args=[p.pk]), {"outcome": "succeeded"}, **H
    )
    assert response.status_code == 404


def test_delivered_and_dispute_with_evidence():
    p = shipped()
    shop = signed_in(p.seller)
    proof = picture(p.seller)
    delivered = shop.post(
        reverse("v1:payment-delivered", args=[p.pk]), {"proof_media_id": str(proof.pk)}, **H
    ).json()
    assert delivered["delivered_at"] and delivered["delivery_proof"]["id"] == str(proof.pk)

    client = signed_in(p.buyer)
    assert (
        client.post(reverse("v1:payment-evidence", args=[p.pk]), {"text": "x"}, **H).status_code
        == 409
    )
    opened = client.post(
        reverse("v1:payment-dispute", args=[p.pk]),
        {"reason": "not_as_described", "description": "Mauvaise couleur"},
        format="json",
        **H,
    )
    assert opened.status_code == 201
    dispute = opened.json()["dispute"]
    assert dispute["status"] == "open" and dispute["conversation_id"]
    added = shop.post(
        reverse("v1:payment-evidence", args=[p.pk]), {"text": "Photo avant envoi"}, **H
    ).json()
    assert len(added["dispute"]["evidence"]) == 2
    refused = client.post(
        reverse("v1:payment-dispute", args=[p.pk]), {"reason": "no_proof"}, format="json", **H
    )
    assert refused.status_code == 400


def test_courier_link_without_account():
    p = paid()
    url = (
        signed_in(p.seller).post(reverse("v1:payment-courier-link", args=[p.pk]), **H).json()["url"]
    )
    token = url.rsplit("/", 1)[1]
    courier = APIClient()
    info = courier.get(reverse("v1:payment-courier", args=[token])).json()
    assert info["reference"] == p.reference and info["seller"] == "Aïcha Tresses"
    assert (
        courier.post(reverse("v1:payment-courier", args=[token]), {"code": code_of(p)}).status_code
        == 204
    )
    assert courier.get(reverse("v1:payment-courier", args=[token])).status_code == 404


def test_webhook_endpoint():
    p = payment()
    signed_in(p.buyer).post(reverse("v1:payment-checkout", args=[p.pk]), **H)
    p.refresh_from_db()
    body, headers = signed_event(EventKind.PAYMENT_SUCCEEDED, p.provider_reference, 11_330, "XOF")
    url = reverse("v1:payment-webhook", args=["fake"])
    meta = {f"HTTP_{k.upper().replace('-', '_')}": v for k, v in headers.items()}
    assert APIClient().post(url, body, content_type="application/json", **meta).status_code == 200
    p.refresh_from_db()
    assert p.status == "held"
    bad = APIClient().post(url, body, content_type="application/json")
    assert bad.status_code == 400
    unknown = reverse("v1:payment-webhook", args=["paypal"])
    assert APIClient().post(unknown, body, content_type="application/json").status_code == 404


def test_tax_profile_endpoint_never_returns_the_number():
    client = signed_in(adult("Awa"))
    assert client.get(reverse("v1:tax-profile")).status_code == 404
    saved = client.put(
        reverse("v1:tax-profile"),
        {
            "legal_name": "Awa K.",
            "address": "Rue 1",
            "city": "Cotonou",
            "country": "BJ",
            "tax_id": "1234567890",
        },
        format="json",
        **H,
    ).json()
    assert saved["tax_id_hint"] == "•••• 7890" and "tax_id" not in saved
    assert client.get(reverse("v1:tax-profile")).json()["legal_name"] == "Awa K."


def test_wallet_of_someone_who_never_sold():
    wallet = signed_in(adult("Awa")).get(reverse("v1:wallet")).json()
    assert wallet["wallets"][0]["currency"] == "XOF" and wallet["payouts"] == []


def test_error_messages_carry_their_figures():
    p = paid()
    response = signed_in(p.seller).post(
        reverse("v1:payment-confirm", args=[p.pk]),
        {"code": "000000"},
        HTTP_ACCEPT_LANGUAGE="fr",
        **H,
    )
    assert response.json()["message"] == "Ce code n'est pas le bon. Essais restants : 4."
    assert response.json()["left"] == 4
