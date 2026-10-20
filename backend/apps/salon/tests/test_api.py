"""Salon API: client file, packages, gift cards, stock with barcode, payments at the salon
and invoices, campaigns and unsubscribe; booking with a gift card; admin pages."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.booking.models import ClientRecord
from apps.booking.services import agenda, appointments
from apps.booking.tests.factories import at, salon, service
from apps.glowpro.tests.factories import premium
from apps.messaging.tests.factories import adult
from apps.salon.services import campaigns, giftcards

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_the_complete_client_file_and_a_package_sold_at_the_salon():
    pro = salon()
    facial = service(pro, ("work", 60), name="Soin visage")
    booked = appointments.book(pro, facial.pk, at(10), user=adult("Awa"))
    record = agenda.record_for(pro, booked)
    me = signed_in(pro.user)
    url = reverse("v1:salon-client", args=[record.pk])
    file = me.patch(
        url,
        {"email": "awa@example.com", "birthday_day": 9, "birthday_month": 1, "email_consent": True},
        format="json",
        **H,
    ).json()
    assert file["premium"] is False and file["birthday_month"] == 1
    assert {c["channel"]: c["granted"] for c in file["consents"]} == {
        "email": True,
        "whatsapp": False,
    }
    refused = me.post(
        reverse("v1:salon-packages"),
        {"service_id": str(facial.pk), "name": "5 soins", "sessions": 5, "price_minor": 50_000},
        format="json",
        **H,
    )
    assert refused.status_code == 403
    premium(pro)
    package = me.post(
        reverse("v1:salon-packages"),
        {"service_id": str(facial.pk), "name": "5 soins", "sessions": 5, "price_minor": 50_000},
        format="json",
        **H,
    ).json()
    sold = me.post(
        reverse("v1:salon-client-package", args=[record.pk]),
        {"package_id": package["id"], "method": "cash"},
        format="json",
        **H,
    )
    assert sold.status_code == 201 and sold.json()["installments"][0]["status"] == "paid"
    used = me.post(reverse("v1:salon-session-use", args=[sold.json()["id"]]), **H).json()
    assert used["sessions_used"] == 1
    assert len(me.get(url).json()["packages"]) == 1
    mine = signed_in(record.client).get(reverse("v1:salon-mine")).json()
    assert mine["packages"][0]["sessions_used"] == 1


def test_gift_cards_bought_online_used_at_the_desk_and_for_a_deposit():
    pro = salon()
    offer = APIClient().get(reverse("v1:salon-offers", args=[pro.slug])).json()
    assert offer["packages"] == [] and offer["gift_cards"]["min_minor"] == 5_000
    bought = signed_in(adult("Grâce")).post(
        reverse("v1:salon-gift-buy", args=[pro.slug]),
        {"amount_minor": 20_000, "recipient_name": "Maman", "message": "Bonne fête"},
        format="json",
        **H,
    )
    assert bought.status_code == 200 and bought.json()["checkout_url"]
    me = signed_in(pro.user)
    card = me.post(
        reverse("v1:salon-gift-cards"),
        {"amount_minor": 10_000, "method": "cash"},
        format="json",
        **H,
    ).json()
    check = me.get(reverse("v1:salon-gift-card-check"), {"code": card["code"]}).json()
    assert check["balance_minor"] == 10_000
    used = me.post(
        reverse("v1:salon-gift-card-redeem"),
        {"code": card["code"], "amount_minor": 4_000},
        format="json",
        **H,
    ).json()
    assert used["balance_minor"] == 6_000
    deposit = service(pro, ("work", 60), deposit_kind="amount", deposit_value=5_000)
    booked = APIClient().post(
        reverse("v1:booking-page", args=[pro.slug]),
        {
            "service_id": str(deposit.pk),
            "start": at(10).isoformat(),
            "guest_name": "Inès",
            "guest_phone": "+2290197000001",
            "gift_card_code": card["code"],
            "marketing_consent": True,
        },
        format="json",
    )
    assert booked.status_code == 201 and booked.json()["checkout_url"] is None
    record = ClientRecord.objects.get(pro=pro, phone="+2290197000001")
    assert campaigns.consents_of(record) == {"email": True, "whatsapp": True}
    assert giftcards.find  # the card now has 1 000 left
    listed = me.get(reverse("v1:salon-gift-cards")).json()
    assert [c["balance_minor"] for c in listed] == [1_000]


def test_stock_scan_move_count_and_consumption():
    pro = salon()
    premium(pro)
    me = signed_in(pro.user)
    item = me.post(
        reverse("v1:salon-stock"),
        {
            "name": "Shampoing",
            "kind": "retail",
            "ean": "4006381333931",
            "quantity": 6,
            "alert_threshold": 2,
        },
        format="json",
        **H,
    ).json()
    assert item["quantity"] == 6 and item["low"] is False
    found = me.get(reverse("v1:salon-stock-ean", args=["4006381333931"])).json()
    assert found["id"] == item["id"]
    assert me.get(reverse("v1:salon-stock-ean", args=["0000000000000"])).status_code == 404
    moved = me.post(
        reverse("v1:salon-stock-move", args=[item["id"]]),
        {"kind": "sale", "quantity": 5},
        format="json",
        **H,
    ).json()
    assert moved["quantity"] == 1 and moved["low"] is True
    counted = me.post(
        reverse("v1:salon-stock-count", args=[item["id"]]), {"counted": 3}, format="json", **H
    ).json()
    assert counted["quantity"] == 3
    history = me.get(reverse("v1:salon-stock-item", args=[item["id"]])).json()
    assert [m["kind"] for m in history] == ["inventory", "sale", "in"]
    svc = service(pro, ("work", 30))
    rows = me.put(
        reverse("v1:salon-consumption", args=[svc.pk]),
        {"rows": [{"item_id": item["id"], "quantity": 1}]},
        format="json",
        **H,
    ).json()
    assert rows == [{"item_id": item["id"], "quantity": 1}]
    assert [i["name"] for i in me.get(reverse("v1:salon-stock"), {"low": "1"}).json()] == []


def test_payments_at_the_salon_receipts_and_documents():
    pro = salon()
    me = signed_in(pro.user)
    methods = me.get(reverse("v1:salon-methods")).json()
    assert methods == {
        "methods": ["cash", "momo"],
        "terminal_configured": False,
        "certified_till": False,
        "currency": "XOF",
    }
    paid = me.post(
        reverse("v1:salon-payments"),
        {"amount_minor": 8_000, "method": "momo", "label": "Brushing", "reference": "MTN-1"},
        format="json",
        **H,
    ).json()
    receipt = me.post(reverse("v1:salon-payment-receipt", args=[paid["id"]]), **H).json()
    assert receipt["kind"] == "receipt" and receipt["number"].startswith("R-")
    pdf = me.get(receipt["pdf_url"])
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    assert signed_in(adult()).get(receipt["pdf_url"]).status_code == 404
    cancelled = me.post(
        reverse("v1:salon-payment-cancel", args=[paid["id"]]),
        {"reason": "Erreur"},
        format="json",
        **H,
    ).json()
    assert cancelled["cancelled"] is True
    docs = me.get(reverse("v1:my-documents")).json()
    assert {d["kind"] for d in docs["results"]} == {"receipt", "credit_note"}
    assert docs["einvoice_connected"] is False and docs["can_send_electronic"] is False
    billing = me.patch(
        reverse("v1:my-billing"), {"registration": "IFU 3202312345678"}, format="json", **H
    ).json()
    assert billing["registration"] == "IFU 3202312345678"


def test_campaigns_and_the_unsubscribe_page():
    pro = salon()
    premium(pro)
    me = signed_in(pro.user)
    created = me.post(
        reverse("v1:salon-campaigns"),
        {
            "name": "Tout le monde",
            "segment": "all",
            "channel": "email",
            "subject": "Hello",
            "body": "Hi",
        },
        format="json",
        **H,
    ).json()
    audience = me.get(reverse("v1:salon-campaign", args=[created["id"]])).json()
    assert audience == {"recipients": 0, "without_consent": 0, "limit": 4, "sent_this_month": 0}
    sent = me.post(reverse("v1:salon-campaign-send", args=[created["id"]]), **H).json()
    assert sent["status"] == "sent" and sent["stats"]["sent"] == 0
    svc = service(pro, ("work", 30))
    booked = appointments.book(pro, svc.pk, at(10), user=adult("Awa"))
    record = agenda.record_for(pro, booked)
    token = campaigns.unsubscribe_token(record, "email")
    page = APIClient().get(reverse("v1:unsubscribe", args=[token])).json()
    assert page["unsubscribed"] is False and page["pro_name"] == pro.display_name
    done = APIClient().post(reverse("v1:unsubscribe", args=[token])).json()
    assert done["unsubscribed"] is True
    assert APIClient().get(reverse("v1:unsubscribe", args=["nope"])).status_code == 404


def test_admin_pages(client):
    pro = salon()
    giftcards.sell_on_site(pro, amount_minor=10_000, method="cash", actor=pro.user)
    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    for name in (
        "salon_package",
        "salon_clientpackage",
        "salon_giftcard",
        "salon_stockitem",
        "salon_onsitepayment",
        "salon_campaign",
        "salon_marketingconsent",
        "invoicing_document",
        "invoicing_issuer",
    ):
        assert client.get(reverse(f"admin:{name}_changelist")).status_code == 200
