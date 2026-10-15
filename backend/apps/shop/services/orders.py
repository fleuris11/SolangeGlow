"""The life of an order on the seller's side, and its link with the secure payment.

New (paid) → being prepared → shipped (parcel photo + tracking) or ready to pick up →
handed over (receipt code, money to the seller). The money states come from the payment
(module 5), which calls `on_payment_change` at every move.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment

from .. import errors
from ..models import DeliveryMode, FlashSale, Order, Product, Variant

OS = Order.Status
PS = Payment.Status


def _locked(order: Order) -> Order:
    return Order.objects.select_for_update().select_related("payment", "pro").get(pk=order.pk)


def _seller_only(order: Order, user) -> None:
    if order.pro.user_id != user.pk:
        raise errors.OrderNotFound()


@transaction.atomic
def start_preparing(user, order: Order) -> Order:
    order = _locked(order)
    _seller_only(order, user)
    if order.status != OS.NEW:
        raise errors.InvalidStep()
    order.status = OS.PREPARING
    order.preparing_at = timezone.now()
    order.save(update_fields=["status", "preparing_at", "updated_at"])
    record("shop.order_preparing", order, actor=user)
    transaction.on_commit(
        lambda: notify(
            order.buyer,
            "shop.order_preparing",
            {"reference": order.reference, "shop": order.pro.display_name},
            link=f"/orders/{order.pk}",
        )
    )
    return order


@transaction.atomic
def ship(user, order: Order, *, proof_media_id, carrier: str = "", tracking_number: str = ""):
    """Handed to the delivery: a photo of the parcel, the carrier and its tracking number."""
    order = _locked(order)
    _seller_only(order, user)
    if order.status not in (OS.NEW, OS.PREPARING) or order.delivery_mode == DeliveryMode.PICKUP:
        raise errors.InvalidStep()
    proof = MediaAsset.objects.filter(
        pk=proof_media_id, owner=user, purpose="delivery_proof"
    ).first()
    if proof is None or proof.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED):
        raise errors.ParcelPhotoNeeded()
    payment_services.ship(
        order.payment,
        actor=user,
        carrier=(carrier or order.partner_name).strip(),
        tracking_number=tracking_number,
    )
    order.status = OS.SHIPPED
    order.shipping_proof = proof
    order.save(update_fields=["status", "shipping_proof", "updated_at"])
    return order


@transaction.atomic
def ready_for_pickup(user, order: Order) -> Order:
    order = _locked(order)
    _seller_only(order, user)
    if order.status not in (OS.NEW, OS.PREPARING) or order.delivery_mode != DeliveryMode.PICKUP:
        raise errors.InvalidStep()
    payment_services.ship(order.payment, actor=user)
    order.status = OS.READY
    order.save(update_fields=["status", "updated_at"])
    return order


def cancel(user, order: Order) -> Order:
    """The client while it is new, the seller until she ships: everything is refunded."""
    if user.pk not in (order.buyer_id, order.pro.user_id):
        raise errors.OrderNotFound()
    if order.status not in (OS.NEW, OS.PREPARING):
        raise errors.InvalidStep()
    payment_services.cancel(order.payment, actor=user)
    order.refresh_from_db()
    return order


def may_cancel(payment: Payment, actor) -> bool:
    """Rule given to the payment: the client cannot cancel once the seller prepares."""
    order = Order.objects.filter(payment=payment).only("status").first()
    if order is None or actor.pk != payment.buyer_id:
        return True
    return order.status == OS.NEW


# --- Stock and money states ----------------------------------------------------------------------


def _give_stock_back(order: Order) -> list:
    """Once: the variants (and bundle parts) go back to the stock, flash sales too."""
    if order.stock_returned:
        return []
    restocked = []
    for line in order.lines.all():
        parts = line.components or (
            [{"variant": str(line.variant_id), "quantity": line.quantity}]
            if line.variant_id
            else []
        )
        for part in parts:
            variant = Variant.objects.filter(pk=part["variant"]).first()
            if variant is None:
                continue
            if variant.stock == 0:
                restocked.append(variant.pk)
            Variant.objects.filter(pk=variant.pk).update(stock=F("stock") + part["quantity"])
        if line.flash_sale_id:
            FlashSale.objects.filter(pk=line.flash_sale_id, sold_count__gte=line.quantity).update(
                sold_count=F("sold_count") - line.quantity
            )
    order.stock_returned = True
    return restocked


def _count_sold(order: Order) -> None:
    if order.counted_as_sold:
        return
    for line in order.lines.filter(product__isnull=False):
        Product.objects.filter(pk=line.product_id).update(
            sold_count=F("sold_count") + line.quantity
        )
    order.counted_as_sold = True


def on_payment_change(payment: Payment) -> None:
    """Called by the payment after each move (after the commit)."""
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(payment_id=payment.pk).first()
        if order is None:
            return
        status = payment.status
        restocked = []
        if status == PS.HELD and order.status == OS.PENDING_PAYMENT:
            order.status = OS.NEW
        elif status == PS.SHIPPED and order.status in (OS.NEW, OS.PREPARING):
            order.status = OS.READY if order.delivery_mode == DeliveryMode.PICKUP else OS.SHIPPED
        elif status == PS.DISPUTED:
            order.status = OS.DISPUTED
        elif status in (PS.RELEASED, PS.PARTIALLY_REFUNDED):
            order.status = OS.COMPLETED
            order.completed_at = order.completed_at or timezone.now()
            _count_sold(order)
        elif status == PS.CANCELLED:
            order.status = OS.CANCELLED
            order.cancelled_at = timezone.now()
            restocked = _give_stock_back(order)
        elif status == PS.REFUNDED:
            if payment.shipped_at is None:  # the goods never left: back in stock
                order.status = OS.CANCELLED
                restocked = _give_stock_back(order)
            else:
                order.status = OS.REFUNDED
            order.cancelled_at = order.cancelled_at or timezone.now()
        order.save()
    if restocked:
        from . import alerts

        alerts.notify_back_in_stock(restocked)
