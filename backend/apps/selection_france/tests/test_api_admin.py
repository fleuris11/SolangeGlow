"""The France Selection API (catalogue, order, tracking, special requests) and its admin."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.messaging.tests.factories import upload
from apps.pros.tests.factories import picture
from apps.selection_france import services
from apps.selection_france.models import (
    GroupBuy,
    SelectionOrder,
    SelectionPhoto,
    SelectionProduct,
    Shipment,
    SpecialRequest,
)

from .factories import category, client, code_of, order, point, product

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_the_catalogue_is_public():
    item = product(options=["230", "240"])
    product(slug="mini-gloss", title="Mini gloss", aisle="small_prices", purchase_price_cents=499)
    GroupBuy.objects.create(
        product=item,
        target_quantity=20,
        price_xof=22_000,
        ends_at=timezone.now() + datetime.timedelta(days=3),
    )
    page = APIClient().get(reverse("v1:selection-products")).json()
    assert len(page["results"]) == 2 and page["grouped"]["from"] < page["grouped"]["to"]
    small = APIClient().get(reverse("v1:selection-products"), {"aisle": "small_prices"}).json()
    assert [p["slug"] for p in small["results"]] == ["mini-gloss"]
    detail = APIClient().get(reverse("v1:selection-product", args=[item.slug])).json()
    assert detail["price_xof"] == 25_300 and detail["express_price_xof"] == 29_100
    assert detail["options"] == ["230", "240"] and detail["group"]["target"] == 20
    assert detail["estimates"]["group"] is not None
    assert APIClient().get(reverse("v1:selection-product", args=["nope"])).status_code == 404
    point()
    assert len(APIClient().get(reverse("v1:selection-pickup-points")).json()) == 1


def test_order_pay_and_follow_through_the_api():
    item = product()
    where = point()
    buyer = client()
    api = signed_in(buyer)
    created = api.post(
        reverse("v1:selection-orders"),
        {"product_id": str(item.pk), "shipping_mode": "express", "pickup_point_id": str(where.pk)},
        format="json",
        **H,
    )
    assert created.status_code == 201
    data = created.json()
    assert data["total_xof"] == 29_100 and data["can"]["pay"]
    assert data["payment"]["checkout_url"].endswith(f"/pay/test/{data['payment']['id']}")
    assert data["payment"]["buyer_fee_minor"] == 0
    assert api.post(reverse("v1:selection-order-pay", args=[data["id"]]), **H).status_code == 200
    paid = api.post(
        reverse("v1:payment-test-outcome", args=[data["payment"]["id"]]),
        {"outcome": "succeeded"},
        format="json",
        **H,
    ).json()
    assert len(paid["receipt_code"]) == 6
    seen = api.get(reverse("v1:selection-order", args=[data["id"]])).json()
    assert seen["status"] == "to_order" and seen["can"]["cancel"]
    assert seen["pickup_point"]["city"] == "Cotonou"
    assert api.get(reverse("v1:selection-orders")).json()["results"][0]["id"] == data["id"]
    cancelled = api.post(reverse("v1:selection-order-cancel", args=[data["id"]]), **H).json()
    assert cancelled["status"] == "refunded"
    other = signed_in(client("Inès"))
    assert other.get(reverse("v1:selection-order", args=[data["id"]])).status_code == 404


def test_special_request_through_the_api():
    buyer = client()
    api = signed_in(buyer)
    photo = upload(buyer, purpose="selection_request")
    created = api.post(
        reverse("v1:selection-requests"),
        {"photo": str(photo.pk), "note": "Ce sac en noir"},
        format="json",
        **H,
    )
    assert created.status_code == 201 and created.json()["status"] == "new"
    empty = api.post(reverse("v1:selection-requests"), {"note": "?"}, format="json", **H)
    assert empty.json()["code"] == "request_needs_something"
    request = SpecialRequest.objects.get()
    request.title, request.purchase_price_cents, request.weight_grams = "Sac", 5_000, 500
    request.category = category("accessories")
    request.save()
    services.send_quote(request, actor=None)
    mine = api.get(reverse("v1:selection-requests")).json()
    assert mine[0]["status"] == "quoted" and mine[0]["price_xof"] > 0
    ordered = api.post(
        reverse("v1:selection-request-order", args=[request.pk]),
        {"shipping_mode": "grouped", "pickup_point_id": str(point().pk)},
        format="json",
        **H,
    )
    assert ordered.status_code == 201 and ordered.json()["title"] == "Sac"
    second = services.create_request(buyer, link="https://example.com/x")
    declined = api.post(reverse("v1:selection-request-decline", args=[second.pk]), **H).json()
    assert declined["status"] == "declined"


# --- Admin ---------------------------------------------------------------------------------------


@pytest.fixture
def team(client):
    admin_user = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(admin_user)
    return client


def test_admin_lists_and_the_price_calculation(team):
    item = product()
    for name in (
        "selectionproduct",
        "selectioncategory",
        "selectionorder",
        "shipment",
        "specialrequest",
        "groupbuy",
        "pickuppoint",
    ):
        assert team.get(reverse(f"admin:selection_france_{name}_changelist")).status_code == 200
    page = team.get(reverse("admin:selection_france_selectionproduct_change", args=[item.pk]))
    assert page.status_code == 200 and "25" in page.content.decode()
    team.post(
        reverse("admin:selection_france_selectionproduct_changelist"),
        {"action": "reprice", "_selected_action": [str(item.pk)]},
    )
    team.post(
        reverse("admin:selection_france_selectioncategory_changelist"),
        {"action": "reprice_products", "_selected_action": [str(item.category_id)]},
    )


def test_admin_adds_a_photo(team):
    item = product()
    data = {
        "title": item.title,
        "slug": item.slug,
        "aisle": item.aisle,
        "category": str(item.category_id),
        "availability": "available",
        "merchant_name": item.merchant_name,
        "merchant_url": item.merchant_url,
        "purchase_price_cents": "2500",
        "weight_grams": "300",
        "options": "[]",
        "description": "",
        "photos-TOTAL_FORMS": "1",
        "photos-INITIAL_FORMS": "0",
        "photos-MIN_NUM_FORMS": "0",
        "photos-MAX_NUM_FORMS": "1000",
        "photos-0-position": "0",
        "photos-0-upload": picture(),
    }
    answer = team.post(
        reverse("admin:selection_france_selectionproduct_change", args=[item.pk]), data
    )
    assert answer.status_code == 302, answer.content[:500]
    item.refresh_from_db()
    assert item.price_xof > 25_300 and SelectionPhoto.objects.filter(product=item).exists()


def test_admin_order_journey(team):
    placed = order()
    url = lambda name: reverse(f"admin:selection_france_selectionorder_{name}", args=[placed.pk])  # noqa: E731
    assert team.get(url("change")).status_code == 200
    assert team.get(url("ordered_detail")).status_code == 200
    team.post(url("ordered_detail"), {"merchant_order_number": "SEPH-9"})
    team.get(url("received_detail"))
    placed.refresh_from_db()
    assert placed.status == SelectionOrder.Status.RECEIVED
    team.get(url("received_detail"))  # twice: an error message, nothing changes
    changelist = reverse("admin:selection_france_selectionorder_changelist")
    answer = team.post(changelist, {"action": "to_shipment", "_selected_action": [str(placed.pk)]})
    shipment = Shipment.objects.get()
    assert answer.status_code == 302
    team.post(changelist, {"action": "to_shipment", "_selected_action": [str(placed.pk)]})
    ship_url = lambda name: reverse(f"admin:selection_france_shipment_{name}", args=[shipment.pk])  # noqa: E731
    assert team.get(ship_url("change")).status_code == 200
    Shipment.objects.filter(pk=shipment.pk).update(carrier="DHL", tracking_number="DHL1")
    team.get(ship_url("depart_detail"))
    team.get(ship_url("arrive_detail"))
    assert team.get(url("code_detail")).status_code == 200
    team.post(url("code_detail"), {"code": code_of(placed)})
    placed.refresh_from_db()
    assert placed.status == SelectionOrder.Status.COMPLETED


def test_admin_quotes_a_request(team):
    request = services.create_request(client(), link="https://www.zara.com/robe")
    url = lambda name: reverse(f"admin:selection_france_specialrequest_{name}", args=[request.pk])  # noqa: E731
    assert team.get(url("change")).status_code == 200
    team.get(url("quote_detail"))  # incomplete: an error message
    request.title, request.purchase_price_cents, request.weight_grams = "Robe", 4_000, 400
    request.category = category("fashion")
    request.save()
    assert "Robe" in team.get(url("change")).content.decode()
    team.get(url("quote_detail"))
    request.refresh_from_db()
    assert request.status == SpecialRequest.Status.QUOTED
    other = services.create_request(client("Inès"), link="https://example.com")
    refuse = reverse("admin:selection_france_specialrequest_refuse_detail", args=[other.pk])
    assert team.get(refuse).status_code == 200
    team.post(refuse, {"answer": "Interdit à l'import"})
    other.refresh_from_db()
    assert other.status == SpecialRequest.Status.REFUSED


def test_admin_group_progress(team):
    item = product()
    group = GroupBuy.objects.create(
        product=item,
        target_quantity=10,
        price_xof=20_000,
        ends_at=timezone.now() + datetime.timedelta(days=2),
    )
    page = team.get(reverse("admin:selection_france_groupbuy_change", args=[group.pk]))
    assert "0 / 10" in page.content.decode()
    assert SelectionProduct.objects.count() == 1
