"""Paid at the hand-over: the order goes to the seller at once, without any payment; the client
pays the seller at the delivery or at the pick-up, outside the app."""

import pytest
from django.urls import reverse

from apps.core.models import FeatureFlag
from apps.core.tests.factories import PlatformSettingFactory
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.shop import errors
from apps.shop.models import Order, PaymentMethod, Variant
from apps.shop.services import cart, catalog, checkout, orders

from .factories import buyer, choice, delivers, product, shop_owner

pytestmark = pytest.mark.django_db
O = Order.Status  # noqa: E741


def close_payments():
    FeatureFlag.objects.update_or_create(
        key="payments_closed", defaults={"name": "Payments closed", "is_enabled": True}
    )


def hand_over_order(client=None, item=None, *, mode="pickup", quantity=1):
    client = client or buyer()
    item = item or product()
    owner = item.pro.user
    zone = delivers(owner, mode=mode) if mode != "pickup" else None
    cart.add(client, variant_id=item.variants.get().pk, quantity=quantity)
    group, placed = checkout.place_orders(
        client,
        [choice(owner, mode, zone)],
        address="Rue 12.345, Fidjrossè",
        phone="+2290197123456",
        pay=checkout.HAND_OVER,
    )
    assert group is None
    return placed[0]


def test_the_quote_has_no_buyer_fee_at_the_hand_over():
    client = buyer()
    item = product()
    owner = item.pro.user
    zone = delivers(owner, fee=1_000)
    cart.add(client, variant_id=item.variants.get().pk)
    [online] = checkout.quote(client, [choice(owner, "seller", zone)], pay=checkout.ONLINE)
    [hand] = checkout.quote(client, [choice(owner, "seller", zone)], pay=checkout.HAND_OVER)
    assert online.buyer_fee_minor > 0 and online.hand_over_ok
    assert hand.buyer_fee_minor == 0 and hand.total_minor == 9_000


def test_closed_payments_choose_the_hand_over_by_default():
    client = buyer()
    item = product()
    cart.add(client, variant_id=item.variants.get().pk)
    assert checkout.quote(client, [choice(item.pro.user)])[0].pay == checkout.ONLINE
    close_payments()
    assert checkout.default_pay() == checkout.HAND_OVER
    group, [placed] = checkout.place_orders(client, [choice(item.pro.user)])
    assert group is None and placed.payment_method == PaymentMethod.ON_PICKUP


def test_the_order_goes_to_the_seller_at_once():
    item = product(stock=3)
    placed = hand_over_order(item=item, mode="seller")
    assert placed.status == O.NEW and placed.payment is None
    assert placed.payment_method == PaymentMethod.ON_DELIVERY and placed.paid_at_hand_over
    assert placed.reference.startswith("SG-") and not Payment.objects.exists()
    assert Variant.objects.get(product=item).stock == 2
    note = Notification.objects.get(user=item.pro.user, event_key="shop.order_new")
    assert placed.reference in note.title and "9" in note.body  # 8 000 + 1 000 delivery


def test_delivered_paid_and_closed_by_the_seller():
    placed = hand_over_order(mode="seller")
    owner = placed.pro.user
    orders.start_preparing(owner, placed)
    # The parcel photo is a help, not a must: no money waits.
    orders.ship(owner, placed, proof_media_id=None)
    placed.refresh_from_db()
    assert placed.status == O.SHIPPED
    assert Notification.objects.filter(user=placed.buyer, event_key="shop.order_on_the_way")
    with pytest.raises(errors.OrderNotFound):
        orders.hand_over(placed.buyer, placed)
    orders.hand_over(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.COMPLETED and placed.completed_at
    assert placed.lines.get().product.sold_count == 1
    assert Notification.objects.filter(user=placed.buyer, event_key="shop.order_handed_over")
    with pytest.raises(errors.InvalidStep):
        orders.hand_over(owner, placed)


def test_ready_to_pick_up_and_paid_there():
    placed = hand_over_order()
    owner = placed.pro.user
    orders.ready_for_pickup(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.READY
    assert Notification.objects.filter(user=placed.buyer, event_key="shop.order_ready")
    orders.hand_over(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.COMPLETED


def test_the_client_never_came_the_seller_cancels_and_the_stock_comes_back():
    item = product(stock=1)
    placed = hand_over_order(item=item)
    owner = placed.pro.user
    orders.ready_for_pickup(owner, placed)
    with pytest.raises(errors.InvalidStep):
        orders.cancel(placed.buyer, placed)  # the client only while it is new
    orders.cancel(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED and placed.stock_returned
    assert Variant.objects.get(product=item).stock == 1
    assert Notification.objects.filter(user=placed.buyer, event_key="shop.order_cancelled")
    with pytest.raises(errors.InvalidStep):
        orders.cancel(owner, placed)


def test_the_client_cancels_a_new_order():
    placed = hand_over_order()
    orders.cancel(placed.buyer, placed)
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED
    assert Notification.objects.filter(user=placed.pro.user, event_key="shop.order_cancelled")


def test_a_shop_that_does_not_take_it():
    client = buyer()
    item = product()
    owner = item.pro.user
    zone = delivers(owner)
    cart.add(client, variant_id=item.variants.get().pk)
    catalog.update_shop(owner, pay_on_delivery=False)
    with pytest.raises(errors.HandOverNotAccepted):
        checkout.quote(client, [choice(owner, "seller", zone)], pay=checkout.HAND_OVER)
    assert checkout.quote(client, [choice(owner)], pay=checkout.HAND_OVER)[0].hand_over_ok
    catalog.update_shop(owner, pay_on_pickup=False)
    with pytest.raises(errors.HandOverNotAccepted):
        checkout.quote(client, [choice(owner)], pay=checkout.HAND_OVER)


def test_the_platform_can_turn_it_off():
    client = buyer()
    item = product()
    cart.add(client, variant_id=item.variants.get().pk)
    PlatformSettingFactory(key="shop.hand_over_payment", value="false", value_type="boolean")
    with pytest.raises(errors.HandOverNotAccepted):
        checkout.quote(client, [choice(item.pro.user)], pay=checkout.HAND_OVER)


def test_too_many_orders_to_pay_at_the_hand_over():
    PlatformSettingFactory(key="shop.hand_over_max_open", value="2")
    client = buyer()
    first = hand_over_order(client, product(shop_owner("Gloria")))
    hand_over_order(client, product(shop_owner("Inès")))
    item = product(shop_owner("Fatou"))
    cart.add(client, variant_id=item.variants.get().pk)
    with pytest.raises(errors.TooManyUnpaid) as caught:
        checkout.place_orders(client, [choice(item.pro.user)], pay=checkout.HAND_OVER)
    assert caught.value.details == {"max": 2}
    orders.hand_over(first.pro.user, first)  # received: room for one more
    checkout.place_orders(client, [choice(item.pro.user)], pay=checkout.HAND_OVER)


def test_the_api_from_the_cart_to_the_hand_over(api_client):
    close_payments()
    client = buyer()
    item = product()
    owner = item.pro.user
    cart.add(client, variant_id=item.variants.get().pk)
    api_client.force_authenticate(client)
    body = {"shops": [{"pro_id": str(item.pro.pk), "delivery_mode": "pickup"}]}
    quote = api_client.post(reverse("v1:shop-quote"), body, format="json").json()
    assert quote["pay"] == "hand_over" and quote["online_open"] is False
    assert quote["orders"][0]["hand_over"] is True and quote["orders"][0]["buyer_fee_minor"] == 0
    answer = api_client.post(reverse("v1:shop-checkout"), body, format="json")
    assert answer.status_code == 201, answer.content
    result = answer.json()
    assert result["group_id"] is None and result["checkout_url"] == ""
    order_id = result["orders"][0]
    seen = api_client.get(reverse("v1:shop-order", args=[order_id])).json()
    assert seen["payment"] is None and seen["payment_method"] == "on_pickup"
    assert seen["total_minor"] == 8_000 and seen["can"]["cancel"] is True
    assert seen["can"]["hand_over"] is False  # the seller's button
    api_client.force_authenticate(owner)
    seller_view = api_client.get(reverse("v1:shop-order", args=[order_id])).json()
    assert seller_view["can"]["hand_over"] is True
    done = api_client.post(reverse("v1:shop-order-handed-over", args=[order_id]))
    assert done.status_code == 200 and done.json()["status"] == "completed"
    listed = api_client.get(reverse("v1:shop-orders"), {"role": "seller"}).json()
    assert listed["results"][0]["payment"] is None
    settings_answer = api_client.patch(
        reverse("v1:my-shop"), {"pay_on_delivery": False}, format="json"
    )
    assert settings_answer.status_code == 200, settings_answer.content
    owner.pro_profile.shop.refresh_from_db()
    assert owner.pro_profile.shop.pay_on_delivery is False
