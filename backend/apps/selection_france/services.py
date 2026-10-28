"""France Selection: prices, client orders paid through the secure payment (the platform is
the seller), the team's steps (merchant order, shipments, hand-over), group pre-orders and
special requests.
"""

from __future__ import annotations

import datetime
import secrets
import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.selectors import get_setting
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from . import errors, pricing, selectors
from .models import (
    GroupBuy,
    PickupPoint,
    SelectionOrder,
    SelectionProduct,
    Shipment,
    ShippingMode,
    SpecialRequest,
)

O = SelectionOrder.Status  # noqa: E741
PS = Payment.Status
SOURCE = "selection"
TEAM_GROUP = "Selection France"


def _team():
    """Who prepares the Selection orders: the « Selection France » group, else the owners."""
    User = get_user_model()
    members = User.objects.filter(groups__name=TEAM_GROUP, is_active=True)
    return members if members.exists() else User.objects.filter(is_superuser=True, is_active=True)


def _tell_team(event: str, context: dict, link: str) -> None:
    for member in _team():
        notify(member, event, context, link=link)


def _admin_link(model: str, pk) -> str:
    return f"/admin/selection_france/{model}/{pk}/change/"


# --- Prices ---------------------------------------------------------------------------------------


def reprice(product: SelectionProduct) -> SelectionProduct:
    product.price_xof = pricing.price_of(product).price_xof
    product.express_price_xof = (
        pricing.price_of(product, express=True).price_xof
        if pricing.express_allowed(product.category)
        else None
    )
    product.priced_at = timezone.now()
    product.save(update_fields=["price_xof", "express_price_xof", "priced_at", "updated_at"])
    return product


def reprice_all(products) -> int:
    count = 0
    for product in products.select_related("category"):
        reprice(product)
        count += 1
    return count


def _check_category(category) -> None:
    if category.air_restricted and selectors.blocks_air_restricted():
        raise errors.AirRestricted()


# --- Client orders --------------------------------------------------------------------------------


def _new_reference(prefix: str) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return prefix + "".join(secrets.choice(alphabet) for _ in range(8))


def _pickup(pickup_point_id) -> PickupPoint:
    point = (
        PickupPoint.objects.filter(pk=pickup_point_id, is_active=True).first()
        if pickup_point_id
        else None
    )
    if point is None:
        raise errors.PickupPointNeeded()
    return point


def _check_buyer(buyer) -> None:
    if not can_purchase(buyer):
        raise errors.CannotBuy()
    # Parcels arrive at pick-up points in Benin, prices are in FCFA.
    countries = get_setting("selection.countries", default=["BJ"]) or []
    code = buyer.country.code if buyer.country_id else ""
    if code not in countries or not selectors.selection_enabled(buyer.country):
        raise errors.SelectionUnavailable()


def _create(
    buyer,
    *,
    title: str,
    category,
    option: str,
    quantity: int,
    unit_price: int,
    mode: str,
    point: PickupPoint,
    merchant_name: str,
    merchant_url: str,
    purchase_cents: int,
    product=None,
    special_request=None,
    group_buy=None,
) -> SelectionOrder:
    after = timezone.localtime(group_buy.ends_at).date() if group_buy else None
    first, last = selectors.estimate(mode, after=after)
    order_id = uuid.uuid4()
    total = unit_price * quantity
    payment = payment_services.create_payment(
        buyer,
        selectors.house_account(),
        purpose=Purpose.SELECTION,
        items_minor=total,
        currency="XOF",
        description=f"Sélection France — {title} x{quantity}"[:200],
        delivery_mode=Payment.Delivery.PARTNER,
        category=category.key if category else "",
        source_type=SOURCE,
        source_id=order_id,
        prep_days=selectors.prep_days(mode, after=after),
    )
    order = SelectionOrder.objects.create(
        id=order_id,
        reference=payment.reference,
        buyer=buyer,
        payment=payment,
        product=product,
        special_request=special_request,
        group_buy=group_buy,
        title=title[:140],
        option=option[:60],
        quantity=quantity,
        unit_price_xof=unit_price,
        total_xof=total,
        shipping_mode=mode,
        pickup_point=point,
        merchant_name=merchant_name,
        merchant_url=merchant_url,
        purchase_price_cents=purchase_cents,
        estimate_from=first,
        estimate_to=last,
    )
    record("selection.order_created", order, actor=buyer)
    return order


@transaction.atomic
def place_order(
    buyer,
    product_id,
    *,
    shipping_mode: str,
    pickup_point_id,
    option: str = "",
    quantity: int = 1,
    group: bool = False,
) -> SelectionOrder:
    """An order of a catalogue product (or a place in its group pre-order), to pay now."""
    _check_buyer(buyer)
    product = selectors.on_sale().filter(pk=product_id).first()
    if product is None:
        raise errors.ProductNotFound()
    _check_category(product.category)
    if product.availability != SelectionProduct.Availability.AVAILABLE:
        raise errors.OutOfStock()
    option = (option or "").strip()
    if (product.options and option not in product.options) or (not product.options and option):
        raise errors.InvalidChoice()
    maximum = int(get_setting("selection.max_quantity", default=5))
    if type(quantity) is not int or not 1 <= quantity <= maximum:
        raise errors.InvalidQuantity(details={"max": maximum})
    point = _pickup(pickup_point_id)
    group_buy = None
    if group:
        group_buy = selectors.open_group(product)
        if group_buy is None:
            raise errors.GroupClosed()
        if shipping_mode != ShippingMode.GROUPED:
            raise errors.ExpressUnavailable()
        unit_price = group_buy.price_xof
    elif shipping_mode == ShippingMode.EXPRESS:
        if product.express_price_xof is None:
            raise errors.ExpressUnavailable()
        unit_price = product.express_price_xof
    else:
        unit_price = product.price_xof
    return _create(
        buyer,
        title=product.title,
        category=product.category,
        option=option,
        quantity=quantity,
        unit_price=unit_price,
        mode=shipping_mode,
        point=point,
        merchant_name=product.merchant_name,
        merchant_url=product.merchant_url,
        purchase_cents=product.purchase_price_cents,
        product=product,
        group_buy=group_buy,
    )


@transaction.atomic
def place_gift_order(
    buyer, product_id, *, pickup_point_id, unit_price: int, option: str = ""
) -> SelectionOrder:
    """An offered product (gifts, ADR-014): bought abroad at the price paid by the person
    who offers it, collected at a pick-up point in Benin by the person who receives it."""
    product = selectors.on_sale().filter(pk=product_id).first()
    if product is None:
        raise errors.ProductNotFound()
    _check_category(product.category)
    if product.availability != SelectionProduct.Availability.AVAILABLE:
        raise errors.OutOfStock()
    option = (option or "").strip()
    if (product.options and option not in product.options) or (not product.options and option):
        raise errors.InvalidChoice()
    return _create(
        buyer,
        title=product.title,
        category=product.category,
        option=option,
        quantity=1,
        unit_price=unit_price,
        mode=ShippingMode.GROUPED,
        point=_pickup(pickup_point_id),
        merchant_name=product.merchant_name,
        merchant_url=product.merchant_url,
        purchase_cents=product.purchase_price_cents,
        product=product,
    )


def start_payment(order: SelectionOrder, buyer) -> SelectionOrder:
    """The payment page (the test page in development)."""
    payment_services.start_checkout(order.payment, buyer=buyer)
    order.payment.refresh_from_db()
    return order


def cancel(user, order: SelectionOrder) -> SelectionOrder:
    """The client, before the team bought it: everything is refunded."""
    if order.buyer_id != user.pk:
        raise errors.OrderNotFound()
    if order.status not in (O.TO_ORDER, O.WAITING_GROUP):
        raise errors.InvalidStep()
    payment_services.cancel(order.payment, actor=user)
    order.refresh_from_db()
    return order


def may_cancel(payment: Payment, actor) -> bool:
    order = SelectionOrder.objects.filter(payment=payment).only("status").first()
    if order is None or actor.pk != payment.buyer_id:
        return True
    return order.status in (O.TO_ORDER, O.WAITING_GROUP)


def on_payment_change(payment: Payment) -> None:
    """Called by the payment after each move (after the commit)."""
    with transaction.atomic():
        order = (
            SelectionOrder.objects.select_for_update(of=("self",))
            .select_related("group_buy", "special_request")
            .filter(payment_id=payment.pk)
            .first()
        )
        if order is None:
            return
        status, now = payment.status, timezone.now()
        reached_group = None
        if status == PS.HELD and order.status == O.PENDING_PAYMENT:
            group = order.group_buy
            if group is not None and group.status == GroupBuy.Status.OPEN:
                order.status = O.WAITING_GROUP
                reached_group = group
            else:
                order.status = O.TO_ORDER
                transaction.on_commit(
                    lambda: _tell_team(
                        "selection.order_to_place",
                        {"reference": order.reference, "product": order.title},
                        _admin_link("selectionorder", order.pk),
                    )
                )
            if order.special_request_id:
                SpecialRequest.objects.filter(pk=order.special_request_id).update(
                    status=SpecialRequest.Status.ORDERED
                )
        elif status == PS.SHIPPED:
            order.status = O.SHIPPED
            order.shipped_at = order.shipped_at or now
        elif status == PS.DISPUTED:
            order.status = O.DISPUTED
        elif status in (PS.RELEASED, PS.PARTIALLY_REFUNDED):
            order.status = O.COMPLETED
            order.completed_at = order.completed_at or now
            if order.product_id:
                SelectionProduct.objects.filter(pk=order.product_id).update(
                    sold_count=F("sold_count") + order.quantity
                )
        elif status == PS.CANCELLED:
            order.status = O.CANCELLED
            order.cancelled_at = now
        elif status == PS.REFUNDED:
            order.status = O.REFUNDED
            order.cancelled_at = order.cancelled_at or now
        order.save()
    if reached_group is not None:
        check_group(reached_group)


# --- The team: merchant order, shipments, hand-over -----------------------------------------------


def _step(order: SelectionOrder, *, expected: tuple, target: str, stamp: str, actor) -> None:
    order = SelectionOrder.objects.select_for_update().get(pk=order.pk)
    if order.status not in expected:
        raise errors.InvalidStep()
    order.status = target
    setattr(order, stamp, timezone.now())
    return order


@transaction.atomic
def mark_ordered(order: SelectionOrder, *, actor, merchant_order_number: str) -> SelectionOrder:
    order = _step(order, expected=(O.TO_ORDER,), target=O.ORDERED, stamp="ordered_at", actor=actor)
    order.merchant_order_number = (merchant_order_number or "").strip()[:80]
    order.save()
    record("selection.ordered", order, actor=actor)
    transaction.on_commit(
        lambda: notify(
            order.buyer,
            "selection.ordered",
            {"reference": order.reference, "product": order.title},
            link=f"/selection/orders/{order.pk}",
        )
    )
    return order


@transaction.atomic
def mark_received(order: SelectionOrder, *, actor) -> SelectionOrder:
    order = _step(order, expected=(O.ORDERED,), target=O.RECEIVED, stamp="received_at", actor=actor)
    order.save()
    record("selection.received", order, actor=actor)
    transaction.on_commit(
        lambda: notify(
            order.buyer,
            "selection.received",
            {"reference": order.reference, "product": order.title},
            link=f"/selection/orders/{order.pk}",
        )
    )
    return order


@transaction.atomic
def new_shipment(orders, *, actor) -> Shipment:
    """A batch of orders received in France, all with the same shipping mode."""
    orders = list(SelectionOrder.objects.select_for_update().filter(pk__in=[o.pk for o in orders]))
    if not orders or any(o.status != O.RECEIVED or o.shipment_id for o in orders):
        raise errors.InvalidStep()
    modes = {o.shipping_mode for o in orders}
    if len(modes) != 1:
        raise errors.MixedShipment()
    shipment = Shipment.objects.create(
        reference=_new_reference("LOT-"), mode=modes.pop(), carrier="", tracking_number=""
    )
    SelectionOrder.objects.filter(pk__in=[o.pk for o in orders]).update(shipment=shipment)
    record("selection.shipment_created", shipment, actor=actor)
    return shipment


@transaction.atomic
def depart(shipment: Shipment, *, actor) -> Shipment:
    """The batch leaves France: every order goes « on its way », with the tracking number."""
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    if shipment.status != Shipment.Status.PREPARING:
        raise errors.InvalidStep()
    if not shipment.carrier.strip() or not shipment.tracking_number.strip():
        raise errors.TrackingNeeded()
    house = selectors.house_account()
    d = selectors.delays()
    key = (
        "express_transit_days" if shipment.mode == ShippingMode.EXPRESS else "grouped_transit_days"
    )
    expected = timezone.now() + datetime.timedelta(days=int(d[key][1]))
    for order in shipment.orders.select_related("payment").filter(status=O.RECEIVED):
        payment_services.ship(
            order.payment,
            actor=house,
            carrier=shipment.carrier,
            tracking_number=shipment.tracking_number,
            expected_delivery_at=expected,
        )
    shipment.status = Shipment.Status.DEPARTED
    shipment.departed_at = timezone.now()
    shipment.save(update_fields=["status", "departed_at", "updated_at"])
    record("selection.shipment_departed", shipment, actor=actor)
    return shipment


@transaction.atomic
def arrive(shipment: Shipment, *, actor) -> Shipment:
    """In Benin: the clients are told their parcel waits at their pick-up point."""
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    if shipment.status != Shipment.Status.DEPARTED:
        raise errors.InvalidStep()
    now = timezone.now()
    shipment.status = Shipment.Status.ARRIVED
    shipment.arrived_at = now
    shipment.save(update_fields=["status", "arrived_at", "updated_at"])
    for order in shipment.orders.select_related("buyer", "pickup_point").filter(status=O.SHIPPED):
        order.status = O.ARRIVED
        order.arrived_at = now
        order.save(update_fields=["status", "arrived_at", "updated_at"])
        transaction.on_commit(
            lambda o=order: notify(
                o.buyer,
                "selection.arrived",
                {"reference": o.reference, "product": o.title, "place": str(o.pickup_point)},
                link=f"/selection/orders/{o.pk}",
            )
        )
    record("selection.shipment_arrived", shipment, actor=actor)
    return shipment


def hand_over(order: SelectionOrder, code: str, *, actor) -> SelectionOrder:
    """At the pick-up point: the client's code releases the money (to the platform)."""
    if order.status not in (O.ARRIVED, O.SHIPPED):
        raise errors.InvalidStep()
    payment_services.confirm_receipt(order.payment, code, actor=selectors.house_account())
    record("selection.handed_over", order, actor=actor)
    order.refresh_from_db()
    return order


# --- Group pre-orders -----------------------------------------------------------------------------


@transaction.atomic
def check_group(group: GroupBuy) -> GroupBuy:
    """Goal reached: every waiting order goes to the team, the clients are told."""
    group = GroupBuy.objects.select_for_update().get(pk=group.pk)
    if group.status != GroupBuy.Status.OPEN or selectors.group_count(group) < group.target_quantity:
        return group
    group.status = GroupBuy.Status.REACHED
    group.closed_at = timezone.now()
    group.save(update_fields=["status", "closed_at", "updated_at"])
    waiting = list(group.orders.select_related("buyer").filter(status=O.WAITING_GROUP))
    SelectionOrder.objects.filter(pk__in=[o.pk for o in waiting]).update(status=O.TO_ORDER)
    title = group.product.title
    transaction.on_commit(
        lambda: (
            [
                notify(
                    o.buyer,
                    "selection.group_reached",
                    {"product": title},
                    link=f"/selection/orders/{o.pk}",
                )
                for o in waiting
            ],
            _tell_team(
                "selection.order_to_place",
                {"reference": f"{len(waiting)} x", "product": title},
                "/admin/selection_france/selectionorder/?status__exact=to_order",
            ),
        )
    )
    return group


def close_due_groups(now=None) -> dict:
    """At the end date: goal reached (orders go on) or not (each client is refunded)."""
    now = now or timezone.now()
    counts = {"reached": 0, "failed": 0}
    for group in GroupBuy.objects.filter(status=GroupBuy.Status.OPEN, ends_at__lte=now):
        if check_group(group).status == GroupBuy.Status.REACHED:
            counts["reached"] += 1
            continue
        with transaction.atomic():
            locked = GroupBuy.objects.select_for_update().get(pk=group.pk)
            if locked.status != GroupBuy.Status.OPEN:
                continue
            locked.status = GroupBuy.Status.FAILED
            locked.closed_at = now
            locked.save(update_fields=["status", "closed_at", "updated_at"])
        for order in group.orders.select_related("payment", "buyer").filter(status=O.WAITING_GROUP):
            payment_services.refund_full(order.payment, reason="group_failed")
            notify(
                order.buyer,
                "selection.group_failed",
                {"product": group.product.title},
                link=f"/selection/orders/{order.pk}",
            )
        counts["failed"] += 1
    return counts


# --- Special requests -----------------------------------------------------------------------------


def create_request(client, *, link: str = "", photo_id=None, note: str = "") -> SpecialRequest:
    _check_buyer(client)
    link = (link or "").strip()[:500]
    photo = None
    if photo_id:
        photo = MediaAsset.objects.filter(
            pk=photo_id, owner=client, purpose="selection_request"
        ).first()
        if photo is None:
            raise errors.RequestNeedsSomething()
    if not link and photo is None:
        raise errors.RequestNeedsSomething()
    request = SpecialRequest.objects.create(
        client=client, link=link, photo=photo, note=(note or "").strip()[:1000]
    )
    transaction.on_commit(
        lambda: _tell_team(
            "selection.request_new",
            {"name": client.first_name},
            _admin_link("specialrequest", request.pk),
        )
    )
    return request


def quote_breakdown(request: SpecialRequest, *, express: bool = False) -> pricing.Breakdown | None:
    if not (request.purchase_price_cents and request.weight_grams and request.category_id):
        return None
    return pricing.compute(
        request.purchase_price_cents,
        request.weight_grams,
        pricing.params_for(request.category),
        express=express,
    )


def quote_prices(request: SpecialRequest) -> tuple[int, int | None]:
    """(grouped, express) prices of a quote; the express one keeps the team's adjustment."""
    grouped = quote_breakdown(request)
    base = request.price_xof or (grouped.price_xof if grouped else 0)
    if grouped is None or not pricing.express_allowed(request.category):
        return base, None
    express = quote_breakdown(request, express=True)
    return base, base + (express.price_xof - grouped.price_xof)


@transaction.atomic
def send_quote(request: SpecialRequest, *, actor) -> SpecialRequest:
    request = SpecialRequest.objects.select_for_update().get(pk=request.pk)
    if request.status not in (SpecialRequest.Status.NEW, SpecialRequest.Status.QUOTED):
        raise errors.InvalidStep()
    if not request.title.strip() or quote_breakdown(request) is None:
        raise errors.QuoteIncomplete()
    _check_category(request.category)
    request.price_xof = quote_prices(request)[0]
    days = int(get_setting("selection.quote_valid_days", default=7))
    now = timezone.now()
    request.status = SpecialRequest.Status.QUOTED
    request.quoted_at = now
    request.valid_until = now + datetime.timedelta(days=days)
    request.save()
    record("selection.quoted", request, actor=actor)
    transaction.on_commit(
        lambda: notify(
            request.client,
            "selection.quote_ready",
            {"product": request.title},
            link="/selection/requests",
        )
    )
    return request


@transaction.atomic
def refuse_request(request: SpecialRequest, *, actor, answer: str = "") -> SpecialRequest:
    if request.status not in (SpecialRequest.Status.NEW, SpecialRequest.Status.QUOTED):
        raise errors.InvalidStep()
    request.status = SpecialRequest.Status.REFUSED
    request.answer = (answer or request.answer)[:500]
    request.save(update_fields=["status", "answer", "updated_at"])
    record("selection.request_refused", request, actor=actor)
    transaction.on_commit(
        lambda: notify(
            request.client,
            "selection.request_refused",
            {"answer": request.answer},
            link="/selection/requests",
        )
    )
    return request


def decline(client, request: SpecialRequest) -> SpecialRequest:
    if request.client_id != client.pk:
        raise errors.RequestNotFound()
    if request.status not in (SpecialRequest.Status.NEW, SpecialRequest.Status.QUOTED):
        raise errors.InvalidStep()
    request.status = SpecialRequest.Status.DECLINED
    request.save(update_fields=["status", "updated_at"])
    return request


@transaction.atomic
def order_quote(
    client, request: SpecialRequest, *, shipping_mode: str, pickup_point_id
) -> SelectionOrder:
    """She accepts the quote: an order to pay, then the usual journey."""
    request = SpecialRequest.objects.select_for_update().get(pk=request.pk)
    if request.client_id != client.pk:
        raise errors.RequestNotFound()
    _check_buyer(client)
    if request.status != SpecialRequest.Status.QUOTED:
        raise errors.InvalidStep()
    if request.valid_until and request.valid_until <= timezone.now():
        raise errors.QuoteExpired()
    _check_category(request.category)
    point = _pickup(pickup_point_id)
    grouped, express = quote_prices(request)
    if shipping_mode == ShippingMode.EXPRESS and express is None:
        raise errors.ExpressUnavailable()
    previous = SelectionOrder.objects.filter(special_request=request).first()
    if previous is not None:
        if previous.status != O.CANCELLED:
            raise errors.InvalidStep()
        previous.special_request = None
        previous.save(update_fields=["special_request", "updated_at"])
    return _create(
        client,
        title=request.title,
        category=request.category,
        option="",
        quantity=1,
        unit_price=express if shipping_mode == ShippingMode.EXPRESS else grouped,
        mode=shipping_mode,
        point=point,
        merchant_name=request.merchant_name or "",
        merchant_url=request.merchant_url or request.link,
        purchase_cents=request.purchase_price_cents,
        special_request=request,
    )


def expire_quotes(now=None) -> int:
    now = now or timezone.now()
    return SpecialRequest.objects.filter(
        Q(status=SpecialRequest.Status.QUOTED), valid_until__lte=now
    ).update(status=SpecialRequest.Status.EXPIRED, updated_at=now)


def run_all(now=None) -> dict:
    now = now or timezone.now()
    return {"groups": close_due_groups(now), "expired_quotes": expire_quotes(now)}
