"""The shop API: a pro builds her shop, a client buys through two shops and pays once, the
seller hands over with the receipt code, the money reaches her wallet."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.payments.tests.factories import picture
from apps.shop.models import Order

from .factories import buyer, delivers, photo, product, shop_owner

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_a_pro_builds_her_shop():
    owner = shop_owner()
    shop = signed_in(owner)
    settings = shop.patch(
        reverse("v1:my-shop"),
        {"seller_delivery": True, "pickup_note": "9h-18h"},
        format="json",
        **H,
    ).json()
    assert settings["delivery"]["seller_delivery"] and settings["can_sell"] and settings["enabled"]
    zones = shop.post(
        reverse("v1:my-shop-zones"),
        {"mode": "seller", "name": "Cotonou", "fee_minor": 1000},
        format="json",
        **H,
    ).json()["delivery"]["zones"]
    zone_id = zones[0]["id"]
    assert (
        shop.patch(
            reverse("v1:my-shop-zone", args=[zone_id]),
            {"mode": "seller", "name": "Cotonou centre", "fee_minor": 500},
            format="json",
            **H,
        ).json()["delivery"]["zones"][0]["fee_minor"]
        == 500
    )

    created = shop.post(
        reverse("v1:my-products"),
        {
            "title": "Fond de teint Velours",
            "price_minor": 8000,
            "category": "makeup",
            "photos": [str(photo(owner).pk)],
            "variants": [
                {"shade": "Caramel", "swatch": "#A0522D", "stock": 4},
                {"shade": "Ébène", "stock": 0},
            ],
        },
        format="json",
        **H,
    )
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "draft" and len(data["variants"]) == 2
    pid = data["id"]
    published = shop.post(reverse("v1:my-product-publish", args=[pid]), **H).json()
    assert published["status"] == "published"
    variant = published["variants"][1]["id"]
    assert (
        shop.patch(
            reverse("v1:my-variant-stock", args=[variant]), {"stock": 2}, format="json", **H
        ).json()["stock"]
        == 2
    )
    edited = shop.put(
        reverse("v1:my-product", args=[pid]),
        {
            "title": "Fond de teint Velours",
            "price_minor": 7500,
            "category": "makeup",
            "photos": [str(photo(owner).pk)],
            "variants": [{"id": variant, "shade": "Ébène", "stock": 2}],
        },
        format="json",
        **H,
    ).json()
    assert edited["base_price_minor"] == 7500 and len(edited["variants"]) == 1
    assert shop.get(reverse("v1:my-product", args=[pid])).json()["id"] == pid
    assert len(shop.get(reverse("v1:my-products")).json()) == 1
    assert shop.post(reverse("v1:my-product-pause", args=[pid]), **H).json()["status"] == "paused"

    promos = shop.post(
        reverse("v1:my-promos"), {"code": "ete", "percent_off": 10}, format="json", **H
    ).json()["promos"]
    assert promos[0]["code"] == "ETE" and promos[0]["uses"] == 0
    promo_id = promos[0]["id"]
    shop.patch(
        reverse("v1:my-promo", args=[promo_id]),
        {"code": "ETE", "percent_off": 15},
        format="json",
        **H,
    )
    now = timezone.now()
    sales = shop.post(
        reverse("v1:my-flash-sales"),
        {
            "product_id": pid,
            "percent_off": 20,
            "starts_at": (now + datetime.timedelta(hours=1)).isoformat(),
            "ends_at": (now + datetime.timedelta(hours=5)).isoformat(),
        },
        format="json",
        **H,
    ).json()["flash_sales"]
    assert sales[0]["product_title"] == "Fond de teint Velours"
    shop.delete(reverse("v1:my-flash-sale", args=[sales[0]["id"]]), **H)
    other = product(owner, title="Gloss Miel", price=3000)
    bundles = shop.post(
        reverse("v1:my-bundles"),
        {
            "title": "Duo",
            "price_minor": 9000,
            "items": [{"variant_id": variant}, {"variant_id": str(other.variants.get().pk)}],
        },
        format="json",
        **H,
    ).json()["bundles"]
    assert bundles[0]["worth_minor"] == 10_500
    shop.patch(
        reverse("v1:my-bundle", args=[bundles[0]["id"]]),
        {
            "title": "Duo",
            "price_minor": 8000,
            "items": [{"variant_id": variant}, {"variant_id": str(other.variants.get().pk)}],
        },
        format="json",
        **H,
    )
    everything = shop.get(reverse("v1:my-promotions")).json()
    assert everything["bundles"][0]["price_minor"] == 8000 and not everything["flash_sales"]
    shop.delete(reverse("v1:my-bundle", args=[bundles[0]["id"]]), **H)
    shop.delete(reverse("v1:my-promo", args=[promo_id]), **H)
    shop.delete(reverse("v1:my-shop-zone", args=[zone_id]), **H)
    assert shop.get(reverse("v1:my-shop-stats")).json()["orders"] == 0
    assert shop.delete(reverse("v1:my-product", args=[pid]), **H).status_code == 204
    assert shop.get(reverse("v1:my-product", args=[pid])).status_code == 404


def test_forbidden_product_answer():
    owner = shop_owner()
    item = product(owner, title="Savon au mercure", publish=False)
    answer = signed_in(owner).post(reverse("v1:my-product-publish", args=[item.pk]), **H)
    assert answer.status_code == 400 and answer.json()["code"] == "forbidden_product"
    assert "mercure" in answer.json()["message"]


def test_a_client_who_is_not_a_pro_has_no_shop():
    assert signed_in(buyer()).get(reverse("v1:my-shop")).json()["code"] == "not_a_pro"


def test_shop_page_and_product_page_are_public():
    item = product(variants=[{"shade": "Caramel", "stock": 0}, {"shade": "Miel", "stock": 3}])
    pro = item.pro
    page = APIClient().get(reverse("v1:shop-page", args=[pro.slug])).json()
    assert page["shop"]["name"] == pro.display_name and page["products"][0]["in_stock"]
    assert page["categories"][0]["key"] == "makeup" and page["bundles"] == []
    detail = APIClient().get(reverse("v1:shop-product-by-slug", args=[pro.slug, item.slug])).json()
    assert [v["shade"] for v in detail["variants"]] == ["Caramel", "Miel"]
    assert detail["link"] == f"/{pro.slug}/shop/{item.slug}" and not detail["is_mine"]
    assert APIClient().get(reverse("v1:shop-product", args=[item.pk])).json()["id"] == str(item.pk)
    assert APIClient().get(reverse("v1:shop-product-reviews", args=[item.pk])).json()["count"] == 0
    assert len(APIClient().get(reverse("v1:shop-categories")).json()) == 8
    assert APIClient().get(reverse("v1:shop-page", args=["nobody"])).status_code == 404
    assert (
        APIClient().get(reverse("v1:shop-product-by-slug", args=[pro.slug, "x"])).status_code == 404
    )
    assert APIClient().get(reverse("v1:shop-product", args=[pro.pk])).status_code == 404


def test_wishlist_and_stock_alert_through_the_api():
    item = product(variants=[{"shade": "Caramel", "stock": 0}])
    client = buyer()
    api = signed_in(client)
    variant = item.variants.get().pk
    assert api.put(reverse("v1:shop-wishlist-item", args=[item.pk]), **H).status_code == 204
    assert api.put(reverse("v1:shop-alert", args=[variant]), **H).status_code == 204
    detail = api.get(reverse("v1:shop-product", args=[item.pk])).json()
    assert detail["wished"] and detail["watching"] == [str(variant)]
    assert api.get(reverse("v1:shop-wishlist")).json()["results"][0]["id"] == str(item.pk)
    api.delete(reverse("v1:shop-wishlist-item", args=[item.pk]), **H)
    api.delete(reverse("v1:shop-alert", args=[variant]), **H)
    assert api.get(reverse("v1:shop-wishlist")).json()["results"] == []


def test_buy_in_two_shops_pay_once_and_hand_over():
    gloria = shop_owner("Gloria Make-up")
    ines = shop_owner("Inès Ongles")
    foundation = product(gloria)
    polish = product(ines, title="Vernis Rouge", price=2500)
    zone = delivers(gloria)
    client = buyer()
    api = signed_in(client)
    for item in (foundation, polish):
        added = api.post(
            reverse("v1:shop-cart-items"),
            {"variant_id": str(item.variants.get().pk), "quantity": 1},
            format="json",
            **H,
        )
        assert added.status_code == 201
    basket = api.get(reverse("v1:shop-cart")).json()
    assert basket["count"] == 2 and len(basket["shops"]) == 2
    line = basket["shops"][0]["lines"][0]["id"]
    api.patch(reverse("v1:shop-cart-item", args=[line]), {"quantity": 2}, format="json", **H)
    choices = {
        "shops": [
            {
                "pro_id": str(gloria.pro_profile.pk),
                "delivery_mode": "seller",
                "zone_id": str(zone.pk),
            },
            {"pro_id": str(ines.pro_profile.pk), "delivery_mode": "pickup"},
        ]
    }
    quote = api.post(reverse("v1:shop-quote"), choices, format="json", **H).json()
    assert quote["orders"][0]["total_minor"] == 16_000 + 1_000 + 510
    placed = api.post(
        reverse("v1:shop-checkout"),
        {**choices, "address": "Rue 12, Fidjrossè", "phone": "+2290197123456"},
        format="json",
        **H,
    )
    assert placed.status_code == 201
    result = placed.json()
    assert result["checkout_url"].endswith(f"/pay/test/group/{result['group_id']}")
    group = api.get(reverse("v1:payment-group", args=[result["group_id"]])).json()
    assert group["status"] == "pending" and len(group["payments"]) == 2
    assert group["total_minor"] == quote["total_minor"]
    first = result["orders"][0]
    again = api.post(reverse("v1:shop-order-pay", args=[first]), **H).json()
    assert again["group_id"] == result["group_id"]
    paid = api.post(
        reverse("v1:payment-group-test-outcome", args=[result["group_id"]]),
        {"outcome": "succeeded"},
        format="json",
        **H,
    ).json()
    assert paid["status"] == "paid"
    mine = api.get(reverse("v1:shop-orders")).json()["results"]
    assert {o["status"] for o in mine} == {"new"} and mine[0]["payment"] is None
    order = api.get(reverse("v1:shop-order", args=[first])).json()
    code = order["payment"]["receipt_code"]
    assert len(code) == 6 and order["can"]["cancel"] and order["address"]

    seller = signed_in(gloria)
    sold = seller.get(reverse("v1:shop-orders"), {"role": "seller", "status": "active"}).json()
    assert [o["id"] for o in sold["results"]] == [first]
    seen = seller.get(reverse("v1:shop-order", args=[first])).json()
    assert seen["contact_phone"] == "+2290197123456" and seen["payment"]["receipt_code"] is None
    seller.post(reverse("v1:shop-order-prepare", args=[first]), **H)
    proof = picture(gloria)
    shipped = seller.post(
        reverse("v1:shop-order-ship", args=[first]),
        {"proof": str(proof.pk), "carrier": "Moto", "tracking_number": ""},
        format="json",
        **H,
    ).json()
    assert shipped["status"] == "shipped" and shipped["shipping_proof"]
    done = seller.post(
        reverse("v1:payment-confirm", args=[seen["payment"]["id"]]),
        {"code": code},
        format="json",
        **H,
    )
    assert done.status_code == 200
    assert Order.objects.get(pk=first).status == "completed"
    assert seller.get(reverse("v1:wallet")).json()["wallets"][0]["available_minor"] == 17_000

    # The other shop: ready to pick up, the client may not cancel once prepared.
    second = result["orders"][1]
    shop = signed_in(ines)
    shop.post(reverse("v1:shop-order-ready", args=[second]), **H)
    assert api.post(reverse("v1:shop-order-cancel", args=[second]), **H).status_code == 409
    assert api.get(reverse("v1:shop-order", args=[second])).json()["pickup"]["city"] == "Cotonou"
    assert api.get(reverse("v1:shop-order", args=[ines.pk])).status_code == 404


def test_cancel_through_the_api():
    from .factories import order

    placed = order()
    api = signed_in(placed.buyer)
    answer = api.post(reverse("v1:shop-order-cancel", args=[placed.pk]), **H).json()
    assert answer["status"] == "cancelled"
    assert api.post(reverse("v1:shop-order-pay", args=[placed.pk]), **H).status_code == 409


def test_the_payment_of_an_order_points_to_it():
    from .factories import order

    placed = order()
    data = signed_in(placed.buyer).get(reverse("v1:payment", args=[placed.payment_id])).json()
    assert data["source_type"] == "order" and data["source_id"] == str(placed.pk)
    assert data["group_id"] and not data["can"]["pay"]
