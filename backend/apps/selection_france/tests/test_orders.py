"""From the order to the pick-up point: the platform sells, the team buys at the merchant,
ships the batch, the client gets her parcel against her code. Group pre-orders and special
requests follow the same journey."""

import datetime

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.core.models import Country
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory
from apps.messaging.tests.factories import minor, upload
from apps.notifications.models import Notification
from apps.payments import errors as payment_errors
from apps.payments import ledger
from apps.payments.models import LedgerAccount, Payment
from apps.selection_france import errors, selectors, services
from apps.selection_france.models import (
    GroupBuy,
    SelectionOrder,
    SelectionProduct,
    Shipment,
    SpecialRequest,
)

from .factories import category, client, code_of, order, pay, point, product

pytestmark = pytest.mark.django_db
O = SelectionOrder.Status  # noqa: E741


@pytest.fixture
def team():
    member = UserFactory(first_name="Solange", is_staff=True)
    member.groups.add(Group.objects.get(name=services.TEAM_GROUP))
    return member


def later(**kwargs):
    return timezone.now() + datetime.timedelta(**kwargs)


# --- Ordering -------------------------------------------------------------------------------------


def test_the_price_shown_is_the_price_paid():
    placed = order(quantity=2, paid=False)
    payment = placed.payment
    assert placed.unit_price_xof == 25_300 and placed.total_xof == 50_600
    assert payment.purpose == "selection" and payment.buyer_fee_minor == 0
    assert payment.total_minor == 50_600 and payment.commission_minor == 0
    assert payment.seller == selectors.house_account()
    assert placed.status == O.PENDING_PAYMENT and placed.estimate_from < placed.estimate_to
    assert placed.merchant_url.startswith("https://www.sephora.fr")
    assert str(placed) == placed.reference


def test_express_costs_more_and_arrives_sooner():
    grouped = order(paid=False)
    express = order(item=SelectionProduct.objects.get(), mode="express", paid=False)
    assert express.unit_price_xof == 29_100
    assert express.estimate_to < grouped.estimate_to
    assert express.payment.prep_days < grouped.payment.prep_days


def test_paid_goes_to_the_team(team):
    placed = order()
    assert placed.status == O.TO_ORDER
    assert Notification.objects.filter(user=team, event_key="selection.order_to_place").exists()


def test_without_team_the_owners_are_told():
    owner = UserFactory(first_name="Owner", is_superuser=True, is_staff=True)
    order()
    assert Notification.objects.filter(user=owner, event_key="selection.order_to_place").exists()


def test_ordering_rules():
    item = product(options=["230", "240"])
    buyer = client()
    where = point().pk
    with pytest.raises(errors.InvalidChoice):
        services.place_order(buyer, item.pk, shipping_mode="grouped", pickup_point_id=where)
    with pytest.raises(errors.InvalidQuantity):
        services.place_order(
            buyer, item.pk, shipping_mode="grouped", pickup_point_id=where, option="230", quantity=6
        )
    with pytest.raises(errors.PickupPointNeeded):
        services.place_order(
            buyer, item.pk, shipping_mode="grouped", pickup_point_id=None, option="230"
        )
    placed = services.place_order(
        buyer, item.pk, shipping_mode="grouped", pickup_point_id=where, option="240"
    )
    assert placed.option == "240"
    plain = product(slug="mascara")
    with pytest.raises(errors.InvalidChoice):
        services.place_order(
            buyer, plain.pk, shipping_mode="grouped", pickup_point_id=where, option="x"
        )
    plain.availability = SelectionProduct.Availability.OUT_OF_STOCK
    plain.save()
    with pytest.raises(errors.OutOfStock):
        services.place_order(buyer, plain.pk, shipping_mode="grouped", pickup_point_id=where)
    plain.availability = SelectionProduct.Availability.HIDDEN
    plain.save()
    with pytest.raises(errors.ProductNotFound):
        services.place_order(buyer, plain.pk, shipping_mode="grouped", pickup_point_id=where)


def test_who_can_order():
    item = product()
    where = point().pk
    with pytest.raises(errors.CannotBuy):
        services.place_order(minor(), item.pk, shipping_mode="grouped", pickup_point_id=where)
    france = CountryFactory(code="FR", name="France", phone_prefix="+33", timezone="Europe/Paris")
    lea = UserFactory(first_name="Léa", country=france, birth_date=datetime.date(1990, 1, 1))
    with pytest.raises(errors.SelectionUnavailable):
        services.place_order(lea, item.pk, shipping_mode="grouped", pickup_point_id=where)
    assert Country.objects.filter(code="FR").exists()


def test_goods_forbidden_by_air_are_blocked_then_allowed_without_express():
    perfume = product(slug="parfum", category=category("fragrance"))
    buyer, where = client(), point().pk
    with pytest.raises(errors.ProductNotFound):  # not even shown
        services.place_order(buyer, perfume.pk, shipping_mode="grouped", pickup_point_id=where)
    assert not selectors.on_sale().filter(pk=perfume.pk).exists()
    PlatformSettingFactory(
        key="selection.block_air_restricted", value="false", value_type="boolean"
    )
    with pytest.raises(errors.ExpressUnavailable):
        services.place_order(buyer, perfume.pk, shipping_mode="express", pickup_point_id=where)
    assert (
        services.place_order(
            buyer, perfume.pk, shipping_mode="grouped", pickup_point_id=where
        ).unit_price_xof
        == perfume.price_xof
    )


def test_the_client_cancels_until_the_team_buys(team):
    placed = order()
    services.cancel(placed.buyer, placed)
    placed.refresh_from_db()
    assert placed.status == O.REFUNDED
    second = order(item=SelectionProduct.objects.get())
    services.mark_ordered(second, actor=team, merchant_order_number="SEPH-1")
    second.refresh_from_db()
    with pytest.raises(errors.InvalidStep):
        services.cancel(second.buyer, second)
    with pytest.raises(payment_errors.CancelNotAllowed):
        from apps.payments import services as payment_services

        payment_services.cancel(second.payment, actor=second.buyer)
    with pytest.raises(errors.OrderNotFound):
        services.cancel(client("Inès"), second)


# --- The team's journey ---------------------------------------------------------------------------


def test_merchant_order_shipment_arrival_and_hand_over(team):
    first = order()
    second = order(client("Inès"), SelectionProduct.objects.get())
    for placed in (first, second):
        services.mark_ordered(placed, actor=team, merchant_order_number="SEPH-42")
        services.mark_received(placed, actor=team)
    first.refresh_from_db()
    assert first.status == O.RECEIVED and first.merchant_order_number == "SEPH-42"
    assert Notification.objects.filter(user=first.buyer, event_key="selection.received").exists()
    shipment = services.new_shipment([first, second], actor=team)
    assert shipment.mode == "grouped" and shipment.orders.count() == 2
    with pytest.raises(errors.TrackingNeeded):
        services.depart(shipment, actor=team)
    Shipment.objects.filter(pk=shipment.pk).update(carrier="Colis Express", tracking_number="CE1")
    services.depart(shipment, actor=team)
    first.refresh_from_db()
    assert first.status == O.SHIPPED and first.payment.tracking_number == "CE1"
    assert first.payment.status == Payment.Status.SHIPPED
    with pytest.raises(errors.InvalidStep):
        services.depart(shipment, actor=team)
    services.arrive(shipment, actor=team)
    first.refresh_from_db()
    assert first.status == O.ARRIVED
    assert Notification.objects.filter(user=first.buyer, event_key="selection.arrived").exists()
    with pytest.raises(errors.InvalidStep):
        services.arrive(shipment, actor=team)
    services.hand_over(first, code_of(first), actor=team)
    first.refresh_from_db()
    assert first.status == O.COMPLETED and first.completed_at
    house = selectors.house_account()
    assert ledger.balance_of(LedgerAccount.Kind.SELLER_AVAILABLE, "XOF", owner=house) == 25_300
    assert SelectionProduct.objects.get().sold_count == 1
    with pytest.raises(errors.InvalidStep):
        services.hand_over(first, "000000", actor=team)


def test_shipment_rules(team):
    grouped = order()
    express = order(client("Inès"), SelectionProduct.objects.get(), mode="express")
    with pytest.raises(errors.InvalidStep):  # not received yet
        services.new_shipment([grouped], actor=team)
    for placed in (grouped, express):
        services.mark_ordered(placed, actor=team, merchant_order_number="1")
        services.mark_received(placed, actor=team)
    with pytest.raises(errors.MixedShipment):
        services.new_shipment([grouped, express], actor=team)
    with pytest.raises(errors.InvalidStep):
        services.mark_received(grouped, actor=team)


# --- Group pre-orders -----------------------------------------------------------------------------


def group_of(item, target=3, price=21_000, **kwargs):
    return GroupBuy.objects.create(
        product=item, target_quantity=target, price_xof=price, ends_at=later(days=5), **kwargs
    )


def test_the_group_leaves_when_the_goal_is_reached(team):
    item = product()
    group = group_of(item)
    first = order(item=item, group=True, quantity=2)
    assert first.status == O.WAITING_GROUP and first.unit_price_xof == 21_000
    assert first.payment.prep_days > 13  # waits for the end date
    assert selectors.group_count(group) == 2
    second = order(client("Inès"), item, group=True)
    group.refresh_from_db()
    first.refresh_from_db()
    assert group.status == GroupBuy.Status.REACHED and first.status == O.TO_ORDER
    assert Notification.objects.filter(user=first.buyer, event_key="selection.group_reached")
    assert second.status in (O.WAITING_GROUP, O.TO_ORDER)
    second.refresh_from_db()
    assert second.status == O.TO_ORDER
    with pytest.raises(errors.GroupClosed):
        order(client("Zoé"), item, group=True)


def test_a_group_that_fails_is_refunded():
    item = product()
    group = group_of(item, target=5)
    waiting = order(item=item, group=True)
    assert services.close_due_groups(later(days=1)) == {"reached": 0, "failed": 0}
    GroupBuy.objects.filter(pk=group.pk).update(ends_at=later(minutes=-1))
    assert services.run_all()["groups"] == {"reached": 0, "failed": 1}
    waiting.refresh_from_db()
    group.refresh_from_db()
    assert group.status == GroupBuy.Status.FAILED and waiting.status == O.REFUNDED
    assert Notification.objects.filter(user=waiting.buyer, event_key="selection.group_failed")


def test_a_group_reached_at_the_end_date():
    item = product()
    group = group_of(item, target=2)
    order(item=item, group=True, quantity=1, paid=False)
    placed = SelectionOrder.objects.get()
    SelectionOrder.objects.filter(pk=placed.pk).update(status=O.WAITING_GROUP, quantity=2)
    GroupBuy.objects.filter(pk=group.pk).update(ends_at=later(minutes=-1))
    assert services.close_due_groups() == {"reached": 1, "failed": 0}


def test_a_group_goes_by_grouped_shipment_only():
    item = product()
    group_of(item)
    with pytest.raises(errors.ExpressUnavailable):
        order(item=item, group=True, mode="express")


# --- Special requests -----------------------------------------------------------------------------


def test_a_special_request_quoted_then_paid(team):
    buyer = client()
    photo = upload(buyer, purpose="selection_request")
    request = services.create_request(buyer, photo_id=photo.pk, note="Taille 38, en noir")
    assert request.status == SpecialRequest.Status.NEW and str(request)
    assert Notification.objects.filter(user=team, event_key="selection.request_new").exists()
    with pytest.raises(errors.QuoteIncomplete):
        services.send_quote(request, actor=team)
    request.title = "Sac Polène numéro un"
    request.merchant_url = "https://www.polene-paris.com/sac"
    request.purchase_price_cents = 39_000
    request.weight_grams = 900
    request.category = category("accessories")
    request.save()
    quoted = services.send_quote(request, actor=team)
    assert quoted.status == SpecialRequest.Status.QUOTED and quoted.valid_until > timezone.now()
    grouped, express = services.quote_prices(quoted)
    assert grouped == quoted.price_xof and express > grouped
    assert Notification.objects.filter(user=buyer, event_key="selection.quote_ready").exists()
    placed = services.order_quote(
        buyer, quoted, shipping_mode="express", pickup_point_id=point().pk
    )
    assert placed.unit_price_xof == express and placed.merchant_url.endswith("/sac")
    pay(placed)
    quoted.refresh_from_db()
    assert quoted.status == SpecialRequest.Status.ORDERED
    with pytest.raises(errors.InvalidStep):
        services.order_quote(buyer, quoted, shipping_mode="grouped", pickup_point_id=point().pk)


def test_the_team_can_adjust_the_price_of_a_quote(team):
    request = services.create_request(client(), link="https://www.zara.com/robe")
    request.title, request.purchase_price_cents, request.weight_grams = "Robe", 4_000, 400
    request.category = category("fashion")
    request.price_xof = 40_000
    request.save()
    assert services.send_quote(request, actor=team).price_xof == 40_000


def test_request_refusals_and_expiry(team):
    buyer = client()
    with pytest.raises(errors.RequestNeedsSomething):
        services.create_request(buyer, note="Un parfum")
    with pytest.raises(errors.RequestNeedsSomething):
        services.create_request(
            buyer, photo_id=upload(client("Inès"), purpose="selection_request").pk
        )
    first = services.create_request(buyer, link="https://example.com/a")
    services.refuse_request(first, actor=team, answer="Produit interdit à l'import")
    first.refresh_from_db()
    assert first.status == SpecialRequest.Status.REFUSED
    with pytest.raises(errors.InvalidStep):
        services.refuse_request(first, actor=team)
    second = services.create_request(buyer, link="https://example.com/b")
    with pytest.raises(errors.RequestNotFound):
        services.decline(client("Zoé"), second)
    assert services.decline(buyer, second).status == SpecialRequest.Status.DECLINED
    with pytest.raises(errors.InvalidStep):
        services.decline(buyer, second)
    third = services.create_request(buyer, link="https://example.com/c")
    third.title, third.purchase_price_cents, third.weight_grams = "Gel", 1_000, 100
    third.category = category("fragrance")
    third.save()
    with pytest.raises(errors.AirRestricted):
        services.send_quote(third, actor=team)
    third.category = category()
    third.save()
    services.send_quote(third, actor=team)
    SpecialRequest.objects.filter(pk=third.pk).update(valid_until=later(minutes=-1))
    third.refresh_from_db()
    with pytest.raises(errors.QuoteExpired):
        services.order_quote(buyer, third, shipping_mode="grouped", pickup_point_id=point().pk)
    assert services.expire_quotes() == 1
    with pytest.raises(errors.RequestNotFound):
        services.order_quote(client("Ana"), third, shipping_mode="grouped", pickup_point_id=None)


def test_a_cancelled_quote_order_can_be_paid_again(team):
    buyer = client()
    request = services.create_request(buyer, link="https://example.com/a")
    request.title, request.purchase_price_cents, request.weight_grams = "Gel", 1_000, 100
    request.category = category()
    request.save()
    services.send_quote(request, actor=team)
    first = services.order_quote(
        buyer, request, shipping_mode="grouped", pickup_point_id=point().pk
    )
    with pytest.raises(errors.InvalidStep):
        services.order_quote(buyer, request, shipping_mode="grouped", pickup_point_id=point().pk)
    SelectionOrder.objects.filter(pk=first.pk).update(status=O.CANCELLED)
    again = services.order_quote(
        buyer, request, shipping_mode="grouped", pickup_point_id=point().pk
    )
    assert again.special_request_id == request.pk


def test_the_listener_ignores_other_payments():
    from apps.payments.tests.factories import paid

    payment = paid()
    services.on_payment_change(payment)
    assert services.may_cancel(payment, payment.buyer)
