"""The screens of the gifts through the API: offering, the secret page (no account), the
follow-up of the giver, paying with a Glow gift card, permissions."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.booking.tests.factories import NOW, at, salon, service
from apps.core.tests.factories import CountryFactory, CurrencyFactory
from apps.gifts.models import Gift
from apps.messaging.tests.factories import adult
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.shop.tests import factories as shop

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}
MAMAN = "+2290197000777"


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def giver():
    france = CountryFactory(
        code="FR",
        name="France",
        phone_prefix="+33",
        timezone="Europe/Paris",
        default_currency=CurrencyFactory(code="EUR", name="Euro", symbol="€", decimal_places=2),
    )
    return adult("Grâce", country=france, phone="+33612345678")


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def pay(gift_id):
    payment = Payment.objects.get(gift__pk=gift_id)
    payment_services.mark_paid(
        payment, amount_minor=payment.total_minor, currency="EUR", key=f"t:{payment.pk}"
    )


def test_offer_a_service_and_book_it_without_an_account(giver):
    pro = salon()
    braids = service(pro, ("work", 60), name="Tresses", price=15_000)
    anonymous = APIClient()
    quote = anonymous.get("/api/v1/gifts/quote", {"kind": "service", "service": braids.pk})
    assert quote.status_code == 200
    assert quote.json()["value"] == {"amount_minor": 15_000, "currency": "XOF"}
    assert quote.json()["total"]["currency"] == "EUR"

    client = signed_in(giver)
    created = client.post(
        "/api/v1/gifts",
        {
            "kind": "service",
            "service": str(braids.pk),
            "recipient_name": "Maman",
            "recipient_phone": "01 97 00 07 77",
            "occasion": "birthday",
            "message": "Joyeux anniversaire",
        },
        format="json",
        **H,
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert body["checkout_url"] and body["gift"]["status"] == "waiting_payment"
    gift_id = body["gift"]["id"]
    pay(gift_id)
    gift = Gift.objects.get(pk=gift_id)

    page = anonymous.get(f"/api/v1/gifts/open/{gift.token}")
    assert page.status_code == 200
    data = page.json()
    assert data["from_name"] == "Grâce" and data["message"] == "Joyeux anniversaire"
    assert data["thing"]["name"] == "Tresses" and data["code"] is None
    booked = anonymous.post(
        f"/api/v1/gifts/open/{gift.token}/book",
        {"start": at(10).isoformat()},
        format="json",
        **H,
    )
    assert booked.status_code == 201, booked.json()
    assert booked.json()["manage_url"].startswith("/rdv/")
    follow = client.get(f"/api/v1/gifts/{gift_id}").json()
    assert [s["key"] for s in follow["steps"] if s["at"]] == ["paid", "sent", "opened", "used"]
    assert follow["uses"][0]["status"] in ("confirmed", "pending")
    assert follow["uses"][0].get("receipt_code") is None  # the code is for the person only
    assert client.get("/api/v1/gifts").json()[0]["id"] == gift_id


def test_the_page_of_a_gift_is_secret_and_waits_for_its_day(giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    client = signed_in(giver)
    created = client.post(
        "/api/v1/gifts",
        {
            "kind": "service",
            "service": str(braids.pk),
            "recipient_name": "Maman",
            "recipient_phone": MAMAN,
            "send_at": (NOW + datetime.timedelta(days=2)).isoformat(),
        },
        format="json",
        **H,
    ).json()
    anonymous = APIClient()
    gift = Gift.objects.get(pk=created["gift"]["id"])
    assert anonymous.get(f"/api/v1/gifts/open/{gift.token}").status_code == 404  # not paid
    pay(gift.pk)
    locked = anonymous.get(f"/api/v1/gifts/open/{gift.token}").json()
    assert locked["locked"] is True and "message" not in locked
    assert anonymous.get("/api/v1/gifts/open/nope").status_code == 404
    other = signed_in(adult("Autre"))
    assert other.get(f"/api/v1/gifts/{gift.pk}").status_code == 404
    assert other.post(f"/api/v1/gifts/{gift.pk}/cancel", **H).status_code == 404
    cancelled = client.post(f"/api/v1/gifts/{gift.pk}/cancel", **H)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "refunded"


def test_a_glow_card_through_the_api(giver):
    client = signed_in(giver)
    created = client.post(
        "/api/v1/gifts",
        {"kind": "card", "amount_minor": 3_000, "recipient_name": "Awa", "recipient_phone": MAMAN},
        format="json",
        **H,
    ).json()
    pay(created["gift"]["id"])
    card = Gift.objects.get(pk=created["gift"]["id"])
    awa = adult("Awa", phone=MAMAN)
    holder = signed_in(awa)
    page = holder.get(f"/api/v1/gifts/open/{card.token}").json()
    assert page["code"] == card.code and page["balance"]["amount_minor"] == 19_678
    assert holder.post(f"/api/v1/gifts/open/{card.token}/claim", **H).status_code == 200
    assert holder.get("/api/v1/gifts/received").json()[0]["code"] == card.code
    check = holder.post("/api/v1/gifts/cards/check", {"code": card.code}, format="json", **H)
    assert check.status_code == 200 and check.json()["from_name"] == "Grâce"
    order = shop.order(awa, shop.product(price=8_000), paid=False)
    paid = holder.post(
        "/api/v1/gifts/cards/pay",
        {"code": card.code, "group_id": str(order.payment.group_id)},
        format="json",
        **H,
    )
    assert paid.status_code == 200, paid.json()
    assert paid.json()["balance"]["amount_minor"] == 19_678 - order.payment.total_minor
    wrong = holder.post("/api/v1/gifts/cards/pay", {"code": "x"}, format="json", **H)
    assert wrong.status_code == 400
    assert APIClient().post("/api/v1/gifts/cards/check", {"code": card.code}).status_code in (
        401,
        403,
    )


def test_ideas_and_product_options(giver):
    item = shop.product(price=8_000)
    zone = shop.delivers(item.pro.user, fee=1_000)
    anonymous = APIClient()
    ideas = anonymous.get("/api/v1/gifts/ideas").json()
    assert ideas["products"][0]["title"] == item.title
    assert ideas["card_min"] == {"amount_minor": 1_000, "currency": "EUR"}
    options = anonymous.get(f"/api/v1/gifts/products/{item.variants.first().pk}/options").json()
    assert options["pickup"] is True and options["zones"][0]["id"] == str(zone.pk)
