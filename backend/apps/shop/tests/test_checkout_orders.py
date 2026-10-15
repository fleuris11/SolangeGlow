"""From the cart to the money of the seller: one order per shop, one grouped payment,
the stock taken then given back, the life of an order on both sides."""

import datetime

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory
from apps.notifications.models import Notification
from apps.payments import errors as payment_errors
from apps.payments import services as payment_services
from apps.payments.models import Payment, PaymentGroup
from apps.payments.services import groups as group_services
from apps.shop import errors
from apps.shop.models import CartItem, FlashSale, Order, Product, Variant
from apps.shop.services import cart, catalog, checkout, orders

from .factories import (
    buyer,
    choice,
    delivers,
    order,
    pay,
    photo,
    product,
    receipt_code,
    shop_owner,
)

pytestmark = pytest.mark.django_db
O = Order.Status  # noqa: E741


def stock_of(item: Product) -> int:
    return Variant.objects.get(product=item).stock


# --- Cart ----------------------------------------------------------------------------------------


def test_the_cart_groups_lines_by_shop():
    client = buyer()
    gloria = product(shop_owner("Gloria Make-up"), stock=5)
    ines = product(shop_owner("Inès Ongles"), title="Vernis Rouge", price=2_500)
    cart.add(client, variant_id=gloria.variants.get().pk, quantity=2)
    cart.add(client, variant_id=gloria.variants.get().pk)  # adds up
    cart.add(client, variant_id=ines.variants.get().pk)
    shops = cart.cart_summary(client)
    assert [s.pro.display_name for s in shops] == ["Gloria Make-up", "Inès Ongles"]
    assert shops[0].subtotal_minor == 24_000 and shops[0].lines[0].quantity == 3
    assert shops[0].category_key == "makeup" and shops[0].prep_days == 1
    assert cart.count(client) == 2 and str(CartItem.objects.first()).startswith("3 x ")


def test_cart_limits():
    client = buyer()
    item = product(stock=3)
    variant = item.variants.get()
    with pytest.raises(errors.OutOfStock) as caught:
        cart.add(client, variant_id=variant.pk, quantity=4)
    assert caught.value.details == {"title": "Fond de teint Velours", "left": 3}
    assert "3" in caught.value.text()
    with pytest.raises(errors.InvalidQuantity):
        cart.add(client, variant_id=variant.pk, quantity=0)
    PlatformSettingFactory(key="shop.max_quantity_per_line", value="2")
    with pytest.raises(errors.InvalidQuantity):
        cart.add(client, variant_id=variant.pk, quantity=3)
    with pytest.raises(errors.OwnShop):
        cart.add(item.pro.user, variant_id=variant.pk)
    with pytest.raises(errors.ProductNotFound):
        cart.add(client, variant_id=product(publish=False).variants.get().pk)
    PlatformSettingFactory(key="shop.cart_max_lines", value="1")
    cart.add(client, variant_id=variant.pk)
    with pytest.raises(errors.CartFull):
        cart.add(client, variant_id=product(title="Gloss").variants.get().pk)


def test_a_minor_cannot_buy():
    from apps.messaging.tests.factories import minor

    with pytest.raises(errors.CannotBuy):
        cart.add(minor(), variant_id=product().variants.get().pk)


def test_change_and_remove_a_line():
    client = buyer()
    item = product()
    line = cart.add(client, variant_id=item.variants.get().pk)
    assert cart.set_quantity(client, line.pk, 4).quantity == 4
    with pytest.raises(errors.InvalidQuantity):
        cart.set_quantity(client, line.pk, 99)
    assert cart.set_quantity(client, line.pk, 0) is None
    with pytest.raises(errors.ProductNotFound):
        cart.set_quantity(client, line.pk, 1)


# --- Quote and checkout --------------------------------------------------------------------------


def test_quote_with_delivery_and_buyer_protection():
    client = buyer()
    item = product()
    owner = item.pro.user
    zone = delivers(owner, fee=1_000)
    cart.add(client, variant_id=item.variants.get().pk)
    [q] = checkout.quote(client, [choice(owner, "seller", zone)])
    assert (q.subtotal_minor, q.delivery_minor, q.buyer_fee_minor) == (8_000, 1_000, 270)
    assert q.total_minor == 9_270
    [pickup] = checkout.quote(client, [choice(owner)])
    assert pickup.delivery_minor == 0 and pickup.buyer_fee_minor == 240


def test_one_order_per_shop_and_one_payment_for_all():
    client = buyer()
    gloria = product(shop_owner("Gloria Make-up"), stock=5)
    ines = product(shop_owner("Inès Ongles"), title="Vernis Rouge", price=2_500, prep_days=4)
    cart.add(client, variant_id=gloria.variants.get().pk, quantity=2)
    cart.add(client, variant_id=ines.variants.get().pk)
    group, placed = checkout.place_orders(
        client, [choice(gloria.pro.user, note="Merci !"), choice(ines.pro.user)]
    )
    assert len(placed) == 2 and not CartItem.objects.exists()
    assert stock_of(gloria) == 3 and stock_of(ines) == 9
    first, second = placed
    assert first.status == O.PENDING_PAYMENT and first.note == "Merci !"
    assert first.reference == first.payment.reference and str(first) == first.reference
    assert first.payment.source_type == "order" and first.payment.source_id == first.pk
    assert second.payment.prep_days == 4 and second.prep_days == 4
    assert group.total_minor == first.payment.total_minor + second.payment.total_minor
    assert "Fond de teint Velours x2" in first.payment.description
    assert first.lines.get().total_minor == 16_000
    pay(group)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == second.status == O.NEW
    assert receipt_code(first) and receipt_code(second)  # each order has its own code


def test_only_some_shops_of_the_cart():
    client = buyer()
    gloria = product(shop_owner("Gloria Make-up"))
    ines = product(shop_owner("Inès Ongles"), title="Vernis")
    cart.add(client, variant_id=gloria.variants.get().pk)
    cart.add(client, variant_id=ines.variants.get().pk)
    checkout.place_orders(client, [choice(gloria.pro.user)])
    assert [line.title for s in cart.cart_summary(client) for line in s.lines] == ["Vernis"]


def test_checkout_refusals():
    client = buyer()
    item = product()
    owner = item.pro.user
    with pytest.raises(errors.EmptyCart):
        checkout.quote(client, [choice(owner)])
    cart.add(client, variant_id=item.variants.get().pk)
    with pytest.raises(errors.EmptyCart):
        checkout.quote(client, [])
    with pytest.raises(errors.DeliveryNotOffered):
        checkout.quote(client, [choice(owner, "seller")])
    delivers(owner)
    with pytest.raises(errors.ZoneNeeded):
        checkout.quote(client, [choice(owner, "seller")])
    zone = owner.pro_profile.shop.zones.get()
    with pytest.raises(errors.AddressNeeded):
        checkout.place_orders(client, [choice(owner, "seller", zone)], address="Rue 1", phone="12")
    catalog.update_shop(owner, is_open=False)
    with pytest.raises(errors.ShopClosed):
        checkout.quote(client, [choice(owner)])
    catalog.update_shop(owner, is_open=True)
    with pytest.raises(errors.PromoNotFound):
        checkout.quote(client, [choice(owner, promo="NOPE")])


def test_delivery_stays_in_the_country_but_pickup_is_open():
    france = CountryFactory(code="FR", name="France", phone_prefix="+33", timezone="Europe/Paris")
    client = UserFactory(first_name="Léa", country=france, birth_date=datetime.date(1990, 1, 1))
    item = product()
    owner = item.pro.user
    zone = delivers(owner)
    cart.add(client, variant_id=item.variants.get().pk)
    with pytest.raises(errors.OutsideCountry):
        checkout.quote(client, [choice(owner, "seller", zone)])
    assert checkout.quote(client, [choice(owner)])[0].delivery_minor == 0


def test_an_item_gone_meanwhile():
    client = buyer()
    item = product(stock=2)
    owner = item.pro.user
    cart.add(client, variant_id=item.variants.get().pk, quantity=2)
    Variant.objects.filter(product=item).update(stock=1)
    with pytest.raises(errors.OutOfStock):
        checkout.quote(client, [choice(owner)])
    Variant.objects.filter(product=item).update(stock=5)
    catalog.pause(owner, item)
    with pytest.raises(errors.Unavailable):
        checkout.quote(client, [choice(owner)])


def test_stock_taken_by_someone_else_at_the_last_moment(monkeypatch):
    client = buyer()
    item = product(stock=2)
    cart.add(client, variant_id=item.variants.get().pk, quantity=2)
    real_quote = checkout.quote

    def then_sold(*args, **kwargs):
        quotes = real_quote(*args, **kwargs)
        Variant.objects.filter(product=item).update(stock=1)
        return quotes

    monkeypatch.setattr(checkout, "quote", then_sold)
    with pytest.raises(errors.OutOfStock):
        checkout.place_orders(client, [choice(item.pro.user)])
    # Everything is rolled back: no order, the stock as it was before.
    assert not Order.objects.exists() and stock_of(item) == 2


def test_two_currencies_are_paid_separately():
    client = buyer()
    euro = product(shop_owner("Lina Paris", currency="EUR"), title="Gloss", price=1_200)
    xof = product()
    cart.add(client, variant_id=euro.variants.get().pk)
    cart.add(client, variant_id=xof.variants.get().pk)
    with pytest.raises(errors.MixedCurrencies):
        checkout.quote(client, [choice(euro.pro.user), choice(xof.pro.user)])


def test_the_address_and_phone_go_with_a_delivery():
    item = product()
    placed = order(item=item, mode="seller")
    assert placed.address == "Rue 12.345, Fidjrossè" and placed.contact_phone == "+2290197123456"
    assert placed.zone_name == "Cotonou centre" and placed.delivery_minor == 1_000
    pickup = order(buyer("Inès"), product(title="Gloss"))
    assert pickup.address == "" and pickup.contact_phone == ""


# --- Life of an order ----------------------------------------------------------------------------


def test_prepare_ship_and_hand_over_with_the_code():
    placed = order(mode="partner")
    owner = placed.pro.user
    orders.start_preparing(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.PREPARING and placed.preparing_at
    assert Notification.objects.filter(user=placed.buyer, event_key="shop.order_preparing")
    with pytest.raises(errors.ParcelPhotoNeeded):
        orders.ship(owner, placed, proof_media_id=photo(owner).pk)
    orders.ship(
        owner, placed, proof_media_id=photo(owner, "delivery_proof").pk, tracking_number="GZ"
    )
    placed.refresh_from_db()
    assert placed.status == O.SHIPPED and placed.payment.carrier == "Gozem"
    payment_services.confirm_receipt(placed.payment, receipt_code(placed), actor=owner)
    placed.refresh_from_db()
    assert placed.status == O.COMPLETED and placed.completed_at
    item = placed.lines.get().product
    item.refresh_from_db()
    assert item.sold_count == 1


def test_ready_to_pick_up():
    placed = order()
    owner = placed.pro.user
    with pytest.raises(errors.InvalidStep):
        orders.ship(owner, placed, proof_media_id=photo(owner, "delivery_proof").pk)
    orders.ready_for_pickup(owner, placed)
    placed.refresh_from_db()
    assert placed.status == O.READY
    assert Notification.objects.filter(
        user=placed.buyer, event_key="payments.ready_for_pickup"
    ).exists()
    with pytest.raises(errors.InvalidStep):
        orders.ready_for_pickup(owner, placed)


def test_only_the_seller_moves_her_order():
    placed = order()
    with pytest.raises(errors.OrderNotFound):
        orders.start_preparing(placed.buyer, placed)
    with pytest.raises(errors.OrderNotFound):
        orders.cancel(buyer("Stranger"), placed)
    orders.start_preparing(placed.pro.user, placed)
    with pytest.raises(errors.InvalidStep):
        orders.start_preparing(placed.pro.user, placed)


def test_the_client_cancels_a_new_order_and_the_stock_comes_back():
    item = product(stock=1)
    client = buyer()
    from apps.shop.models import StockAlert

    placed = order(client, item)
    waiting = buyer("Zoé")
    StockAlert.objects.create(user=waiting, variant=item.variants.get())
    assert stock_of(item) == 0
    orders.cancel(client, placed)
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED and placed.stock_returned and stock_of(item) == 1
    assert Notification.objects.filter(user=waiting, event_key="shop.back_in_stock").exists()
    with pytest.raises(errors.InvalidStep):
        orders.cancel(client, placed)


def test_the_client_cannot_cancel_once_the_seller_prepares():
    placed = order()
    orders.start_preparing(placed.pro.user, placed)
    with pytest.raises(payment_errors.CancelNotAllowed):
        orders.cancel(placed.buyer, placed)
    # The payment page says so too, and the payment API refuses as well.
    assert not payment_services.may_cancel(placed.payment, placed.buyer)
    assert payment_services.may_cancel(placed.payment, placed.pro.user)
    orders.cancel(placed.pro.user, placed)
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED


def test_not_shipped_in_time_is_refunded_and_restocked():
    from apps.payments.services.automation import cancel_unshipped
    from apps.payments.tests.factories import later

    item = product(stock=3, prep_days=4)
    placed = order(item=item)
    assert not cancel_unshipped(later(days=5))  # 4 days to prepare + 3 to ship
    assert cancel_unshipped(later(days=8)) == 1
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED and stock_of(item) == 3


def test_not_paid_in_time_gives_the_stock_back():
    from apps.payments.services.automation import expire_unpaid
    from apps.payments.tests.factories import later

    item = product(stock=2)
    placed = order(item=item, paid=False)
    assert stock_of(item) == 1
    expire_unpaid(later(hours=1))
    placed.refresh_from_db()
    assert placed.status == O.CANCELLED and stock_of(item) == 2


def test_dispute_and_refund_after_shipping_keeps_the_stock():
    placed = order(mode="seller")
    owner = placed.pro.user
    orders.ship(owner, placed, proof_media_id=photo(owner, "delivery_proof").pk)
    payment_services.open_dispute(placed.payment, reason="damaged", by=placed.buyer)
    placed.refresh_from_db()
    assert placed.status == O.DISPUTED
    payment_services.decide(
        placed.payment.dispute, actor=None, decision="refund", refund_minor=0, note=""
    )
    placed.refresh_from_db()
    assert placed.status == O.REFUNDED and not placed.stock_returned


def test_partial_refund_is_a_finished_order():
    placed = order()
    owner = placed.pro.user
    orders.ready_for_pickup(owner, placed)
    payment_services.open_dispute(placed.payment, reason="not_as_described", by=placed.buyer)
    payment_services.decide(
        placed.payment.dispute, actor=None, decision="partial", refund_minor=2_000, note=""
    )
    placed.refresh_from_db()
    assert placed.status == O.COMPLETED


def test_a_flash_sale_price_and_its_quantity():
    from django.utils import timezone

    from apps.payments.tests.factories import later

    item = product(stock=10)
    sale = FlashSale.objects.create(
        product=item,
        percent_off=25,
        starts_at=timezone.now(),
        ends_at=later(hours=2),
        quantity_limit=2,
    )
    placed = order(item=item, quantity=2)
    line = placed.lines.get()
    assert line.unit_price_minor == 6_000 and line.flash_sale == sale
    sale.refresh_from_db()
    assert sale.sold_count == 2
    # Sold out: the next client pays the normal price.
    second = order(buyer("Inès"), item)
    assert second.lines.get().unit_price_minor == 8_000
    orders.cancel(placed.buyer, placed)
    sale.refresh_from_db()
    assert sale.sold_count == 0


def test_the_listener_ignores_payments_without_order():
    from apps.payments.tests.factories import paid

    payment = paid()
    orders.on_payment_change(payment)  # nothing to do
    assert orders.may_cancel(payment, payment.buyer)


def test_paying_a_grouped_order_again():
    placed = order(paid=False)
    group = placed.payment.group
    again = payment_services.start_group_checkout(group, buyer=placed.buyer)
    assert again.checkout_url.endswith(f"/pay/test/group/{group.pk}")
    assert Payment.objects.get(pk=placed.payment_id).provider_reference == group.provider_reference
    assert group_services.group_status(group) == "pending" and isinstance(group, PaymentGroup)
