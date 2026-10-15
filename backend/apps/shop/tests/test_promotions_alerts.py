"""Promo codes, flash sales, bundles, wishlist and alerts, and what the shop gives to the
other modules (reviews, shared cards, « Buy this product »)."""

import datetime

import pytest
from django.utils import timezone

from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging import errors as messaging_errors
from apps.messaging.shares import resolve
from apps.notifications.models import Notification
from apps.payments import services as payment_services
from apps.shop import errors, links, prices
from apps.shop.models import Bundle, FlashSale, Order, StockAlert, Variant, WishlistItem
from apps.shop.services import alerts, cart, catalog, checkout, orders, promotions
from apps.social import eligibility
from apps.social import services as social_services

from .factories import buyer, choice, order, pay, product, receipt_code, shop_owner

pytestmark = pytest.mark.django_db


def later(**kwargs):
    return timezone.now() + datetime.timedelta(**kwargs)


# --- Promo codes ---------------------------------------------------------------------------------


def test_a_percent_code_in_the_order():
    item = product()
    owner = item.pro.user
    promo = promotions.save_promo(owner, code=" bien venue ", percent_off=10, min_order_minor=5_000)
    assert promo.code == "BIENVENUE" and str(promo) == "BIENVENUE"
    placed = order(item=item, promo="bienvenue")
    assert placed.discount_minor == 800 and placed.items_minor == 7_200
    assert placed.payment.items_minor == 7_200 and placed.promo_label == "BIENVENUE"
    assert promotions.uses_of(promo) == 1


def test_promo_code_rules():
    item = product()
    owner = item.pro.user
    client = buyer()
    cart.add(client, variant_id=item.variants.get().pk)
    promotions.save_promo(owner, code="GROS", amount_off_minor=500, min_order_minor=20_000)
    with pytest.raises(errors.PromoMinimum) as caught:
        checkout.quote(client, [choice(owner, promo="GROS")])
    assert "20" in caught.value.text()
    promotions.save_promo(owner, code="BIENTOT", percent_off=5, starts_at=later(days=1))
    with pytest.raises(errors.PromoOver):
        checkout.quote(client, [choice(owner, promo="BIENTOT")])
    promotions.save_promo(owner, code="FINI", percent_off=5, max_uses=1)
    order(buyer("Inès"), item, promo="FINI")
    with pytest.raises(errors.PromoUsedUp):
        checkout.quote(client, [choice(owner, promo="FINI")])
    once = promotions.save_promo(owner, code="UNE", percent_off=5)
    order(client, product(owner, title="Gloss"), promo="UNE")
    cart.add(client, variant_id=item.variants.get().pk)
    with pytest.raises(errors.PromoUsedUp):
        checkout.quote(client, [choice(owner, promo="UNE")])
    assert promotions.uses_of(once, client) == 1


def test_an_amount_never_makes_the_order_free():
    item = product(price=1_000)
    promotions.save_promo(item.pro.user, code="TOUT", amount_off_minor=5_000)
    placed = order(item=item, promo="TOUT")
    assert placed.items_minor == 1 and placed.discount_minor == 999


@pytest.mark.parametrize(
    "values",
    [
        {"code": "", "percent_off": 5},
        {"code": "A", "percent_off": 5, "amount_off_minor": 5},
        {"code": "A"},
        {"code": "A", "percent_off": 0},
        {"code": "A", "amount_off_minor": -1},
        {"code": "A", "percent_off": 5, "min_order_minor": -1},
        {"code": "A", "percent_off": 5, "max_uses": 0},
        {"code": "A", "percent_off": 5, "ends_at": later(days=-1), "starts_at": later()},
    ],
)
def test_wrong_promo_codes(values):
    with pytest.raises(errors.InvalidPromo):
        promotions.save_promo(shop_owner(), **values)


def test_promo_ceiling_and_names():
    owner = shop_owner()
    with pytest.raises(errors.PromoTooHigh) as caught:
        promotions.save_promo(owner, code="FOU", percent_off=80)
    assert caught.value.details == {"max": 70} and "70" in caught.value.text()
    promo = promotions.save_promo(owner, code="ETE", percent_off=10)
    with pytest.raises(errors.CodeTaken):
        promotions.save_promo(owner, code="ete", percent_off=20)
    changed = promotions.save_promo(owner, promo_id=promo.pk, code="ETE", percent_off=15)
    assert changed.percent_off == 15
    with pytest.raises(errors.PromoNotFound):
        promotions.save_promo(shop_owner("Autre"), promo_id=promo.pk, code="X", percent_off=5)
    promotions.delete_promo(owner, promo.pk)
    with pytest.raises(errors.PromoNotFound):
        promotions.delete_promo(owner, promo.pk)


# --- Flash sales ---------------------------------------------------------------------------------


def test_a_flash_sale_now_and_one_later():
    item = product()
    owner = item.pro.user
    now = timezone.now()
    sale = promotions.create_flash_sale(
        owner, product_id=item.pk, percent_off=20, starts_at=now, ends_at=later(hours=3)
    )
    assert sale.announced_at and str(sale).endswith("-20 %")
    item.refresh_from_db()
    assert prices.lowest_price(item) == (6_400, 8_000)
    with pytest.raises(errors.InvalidFlashSale):  # overlaps
        promotions.create_flash_sale(
            owner, product_id=item.pk, percent_off=10, starts_at=now, ends_at=later(hours=1)
        )
    upcoming = promotions.create_flash_sale(
        owner,
        product_id=item.pk,
        percent_off=10,
        starts_at=later(days=1),
        ends_at=later(days=2),
    )
    item = type(item).objects.get(pk=item.pk)
    assert prices.next_flash_sale(item) == upcoming
    promotions.end_flash_sale(owner, upcoming.pk)  # not started: deleted
    promotions.end_flash_sale(owner, sale.pk)  # running: ends now
    assert not FlashSale.objects.filter(pk=upcoming.pk).exists()
    sale.refresh_from_db()
    assert sale.ends_at <= timezone.now()
    promotions.end_flash_sale(owner, sale.pk)  # already over: nothing
    with pytest.raises(errors.ProductNotFound):
        promotions.end_flash_sale(shop_owner("Autre"), sale.pk)


@pytest.mark.parametrize(
    "values",
    [
        {"percent_off": 95},
        {"ends_at": later(hours=-1)},
        {"ends_at": later(days=9)},
        {"quantity_limit": 0},
    ],
)
def test_wrong_flash_sales(values):
    item = product()
    data = {
        "product_id": item.pk,
        "percent_off": 20,
        "starts_at": timezone.now(),
        "ends_at": later(hours=2),
        **values,
    }
    with pytest.raises(errors.InvalidFlashSale):
        promotions.create_flash_sale(item.pro.user, **data)
    with pytest.raises(errors.ProductNotFound):
        promotions.create_flash_sale(shop_owner("Autre"), **{**data, "percent_off": 20})


def test_rounding_of_a_discount():
    assert prices.percent_off(1_001, 5) == 951
    assert prices.percent_off(999, 50) == 500


# --- Bundles -------------------------------------------------------------------------------------


def test_a_bundle_takes_stock_from_its_products():
    owner = shop_owner()
    foundation = product(owner, stock=5)
    gloss = product(owner, title="Gloss Miel", price=3_000, stock=1)
    bundle = promotions.save_bundle(
        owner,
        title="Routine éclat",
        price_minor=10_000,
        items=[
            {"variant_id": foundation.variants.get().pk, "quantity": 1},
            {"variant_id": gloss.variants.get().pk, "quantity": 1},
        ],
    )
    assert prices.bundle_stock(bundle) == 1 and prices.bundle_worth(bundle) == 11_000
    assert str(bundle) == "Routine éclat" and str(bundle.items.first()).startswith("1 x ")
    client = buyer()
    cart.add(client, bundle_id=bundle.pk)
    with pytest.raises(errors.OutOfStock):
        cart.add(client, bundle_id=bundle.pk)
    group, [placed] = checkout.place_orders(client, [choice(owner)])
    line = placed.lines.get()
    assert line.bundle == bundle and len(line.components) == 2
    assert Variant.objects.get(pk=gloss.variants.get().pk).stock == 0
    pay(group)
    orders.cancel(client, Order.objects.get(pk=placed.pk))
    assert Variant.objects.get(pk=gloss.variants.get().pk).stock == 1


def test_bundle_rules():
    owner = shop_owner()
    item = product(owner)
    variant = item.variants.get()
    with pytest.raises(errors.InvalidBundle):
        promotions.save_bundle(
            owner, title="Seul", price_minor=1, items=[{"variant_id": variant.pk}]
        )
    with pytest.raises(errors.InvalidBundle):
        promotions.save_bundle(
            owner, title="X", price_minor=1, items=[{"variant_id": "nope", "quantity": 2}]
        )
    with pytest.raises(errors.InvalidBundle):
        promotions.save_bundle(
            owner, title="X", price_minor=1, items=[{"variant_id": variant.pk, "quantity": 0}]
        )
    bundle = promotions.save_bundle(
        owner, title="Duo", price_minor=15_000, items=[{"variant_id": variant.pk, "quantity": 2}]
    )
    with pytest.raises(errors.InvalidBundle):
        promotions.save_bundle(
            shop_owner("Autre"),
            bundle_id=bundle.pk,
            title="Duo",
            price_minor=1,
            items=[{"variant_id": variant.pk, "quantity": 2}],
        )
    catalog.pause(owner, item)
    with pytest.raises(errors.ProductNotFound):
        cart.add(buyer(), bundle_id=bundle.pk)
    promotions.delete_bundle(owner, bundle.pk)
    assert not Bundle.objects.exists()
    with pytest.raises(errors.InvalidBundle):
        promotions.delete_bundle(owner, bundle.pk)


# --- Wishlist and alerts -------------------------------------------------------------------------


def test_price_drop_alert_once_a_week():
    item = product()
    owner = item.pro.user
    client = buyer()
    alerts.add_to_wishlist(client, item.pk)
    alerts.add_to_wishlist(client, item.pk)  # once
    catalog.save_product(
        owner,
        product=item,
        title=item.title,
        price_minor=7_500,
        category_key="makeup",
        variants=[{"id": str(item.variants.get().pk), "stock": 10}],
    )
    assert not Notification.objects.filter(event_key="shop.price_drop").exists()  # -6 %
    catalog.save_product(
        owner,
        product=item,
        title=item.title,
        price_minor=6_000,
        category_key="makeup",
        variants=[{"id": str(item.variants.get().pk), "stock": 10}],
    )
    note = Notification.objects.get(user=client, event_key="shop.price_drop")
    assert "8" in note.body and "6" in note.body
    catalog.save_product(
        owner,
        product=item,
        title=item.title,
        price_minor=4_000,
        category_key="makeup",
        variants=[{"id": str(item.variants.get().pk), "stock": 10}],
    )
    assert Notification.objects.filter(event_key="shop.price_drop").count() == 1  # too soon
    item.refresh_from_db()
    assert alerts.check_price_drop(item.pk, later(days=8)) == 1
    # Up again: the next drop counts from the new price.
    catalog.save_product(
        owner,
        product=item,
        title=item.title,
        price_minor=9_000,
        category_key="makeup",
        variants=[{"id": str(item.variants.get().pk), "stock": 10}],
    )
    assert WishlistItem.objects.get().price_seen_minor == 9_000
    alerts.remove_from_wishlist(client, item.pk)
    assert not WishlistItem.objects.exists()
    assert alerts.check_price_drop(item.pk) == 0
    catalog.pause(owner, item)
    assert alerts.check_price_drop(item.pk) == 0
    with pytest.raises(errors.ProductNotFound):
        alerts.add_to_wishlist(client, item.pk)


def test_a_flash_sale_that_starts_alerts_the_wishlists():
    item = product()
    client = buyer()
    alerts.add_to_wishlist(client, item.pk)
    sale = FlashSale.objects.create(
        product=item, percent_off=30, starts_at=later(minutes=-1), ends_at=later(hours=2)
    )
    assert alerts.announce_flash_sales() == 1
    assert alerts.announce_flash_sales() == 0
    sale.refresh_from_db()
    assert sale.announced_at
    assert Notification.objects.filter(user=client, event_key="shop.price_drop").exists()


def test_back_in_stock_alert():
    owner = shop_owner()
    item = product(owner, stock=0)
    variant = item.variants.get()
    client = buyer()
    alerts.watch_stock(client, variant.pk)
    assert StockAlert.objects.count() == 1 and str(StockAlert.objects.get())
    catalog.set_stock(owner, variant.pk, 3)
    assert Notification.objects.filter(user=client, event_key="shop.back_in_stock").exists()
    assert not StockAlert.objects.exists()
    alerts.watch_stock(client, variant.pk)
    alerts.unwatch_stock(client, variant.pk)
    assert not StockAlert.objects.exists()
    catalog.pause(owner, item)
    with pytest.raises(errors.ProductNotFound):
        alerts.watch_stock(client, variant.pk)
    StockAlert.objects.create(user=client, variant=variant)
    assert alerts.notify_back_in_stock([variant.pk]) == 0  # not on sale


def test_a_minor_cannot_wait_for_stock():
    from apps.messaging.tests.factories import minor

    with pytest.raises(errors.CannotBuy):
        alerts.watch_stock(minor(), product(stock=0).variants.get().pk)


# --- What the shop gives to the others -----------------------------------------------------------


def test_a_handed_over_order_opens_a_verified_review():
    placed = order()
    owner = placed.pro.user
    provider = eligibility.provider_for("order")
    found = provider.get(placed.pk)
    assert found.finished_at is None and "Fond de teint Velours" in found.label
    orders.ready_for_pickup(owner, placed)
    payment_services.confirm_receipt(placed.payment, receipt_code(placed), actor=owner)
    assert [t.id for t in provider.finished_for_client(placed.buyer_id)] == [placed.pk]
    assert [t.id for t in provider.finished_for_pro(placed.pro_id)] == [placed.pk]
    review = social_services.create_review(
        placed.buyer, kind="order", transaction_id=placed.pk, rating=5, text="Parfait"
    )
    assert review.pro == placed.pro
    assert provider.get(placed.pro_id) is None


def test_a_product_card_in_a_conversation():
    item = product()
    client = buyer()
    product_id, card = resolve(client, "product", {"id": str(item.pk)})
    assert product_id == item.pk and card["amount_minor"] == 8_000
    assert card["link"] == f"/{item.pro.slug}/shop/{item.slug}"
    with pytest.raises(messaging_errors.ShareNotFound):
        resolve(client, "product", {"id": "nope"})


def test_buy_this_product_on_a_post():
    from apps.social import errors as social_errors
    from apps.social.tests.factories import asset

    item = product()
    owner = item.pro.user
    media = asset(owner)
    post = social_services.create_post(
        owner, kind="photo", media=[{"id": media.pk}], product_id=item.pk
    )
    card = links.post_product_card(post.product_id)
    assert card["title"] == item.title and card["in_stock"]
    with pytest.raises(social_errors.InvalidLink):
        zoe = buyer("Zoé")
        social_services.create_post(
            zoe, kind="photo", media=[{"id": asset(zoe).pk}], product_id=item.pk
        )
    social_services.update_post(post, owner, product_id=None)
    post.refresh_from_db()
    assert post.product_id is None
    with pytest.raises(social_errors.InvalidLink):
        social_services.update_post(post, owner, product_id=product(publish=False).pk)


def test_the_low_stock_and_numbers_of_my_shop():
    from apps.shop.selectors import stats

    owner = shop_owner()
    item = product(owner, stock=2)
    order(item=item)
    data = stats(owner.pro_profile)
    assert data["orders"] == 1 and data["new"] == 1 and data["sales_minor"] == 8_000
    assert data["top"][0]["title"] == item.title
    assert [v.product_id for v in data["running_out"]] == [item.pk]
    PlatformSettingFactory(key="shop.low_stock_threshold", value="0")
    assert not list(stats(owner.pro_profile)["running_out"])
