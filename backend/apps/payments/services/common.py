"""State machine of a secure payment: which move is allowed, done under a row lock,
traced in the audit journal, announced to the module the payment belongs to."""

from __future__ import annotations

from collections.abc import Callable

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record

from .. import errors
from ..models import Payment

S = Payment.Status

ALLOWED: dict[str, set[str]] = {
    S.PENDING_PAYMENT: {S.HELD, S.CANCELLED},
    S.HELD: {S.SHIPPED, S.RELEASED, S.REFUNDED, S.DISPUTED},
    S.SHIPPED: {S.RELEASED, S.DISPUTED},
    S.DISPUTED: {S.RELEASED, S.REFUNDED, S.PARTIALLY_REFUNDED},
    # A payment confirmed after its order was cancelled is refunded at once.
    S.CANCELLED: {S.REFUNDED},
    S.RELEASED: set(),
    S.REFUNDED: set(),
    S.PARTIALLY_REFUNDED: set(),
}

TIMESTAMPS = {
    S.HELD: "paid_at",
    S.SHIPPED: "shipped_at",
    S.DISPUTED: "disputed_at",
    S.RELEASED: "released_at",
    S.REFUNDED: "refunded_at",
    S.PARTIALLY_REFUNDED: "refunded_at",
    S.CANCELLED: "cancelled_at",
}

# Modules that own the payments (shop, bookings…) hear about every change of status,
# and may restrict who cancels (the shop: the client only before the preparation).
_listeners: dict[str, Callable[[Payment], None]] = {}
_cancel_rules: dict[str, Callable[[Payment, object], bool]] = {}


def listen(
    source_type: str,
    callback: Callable[[Payment], None],
    *,
    may_cancel: Callable[[Payment, object], bool] | None = None,
) -> None:
    _listeners[source_type] = callback
    if may_cancel is not None:
        _cancel_rules[source_type] = may_cancel


def forget(source_type: str) -> None:
    _listeners.pop(source_type, None)
    _cancel_rules.pop(source_type, None)


def may_cancel(payment: Payment, actor) -> bool:
    """Paid, not shipped, one of the two parties, and the owner module agrees."""
    if actor is None or actor.pk not in (payment.buyer_id, payment.seller_id):
        return False
    if payment.status != S.HELD:
        return False
    rule = _cancel_rules.get(payment.source_type)
    return rule is None or rule(payment, actor)


def can_move(current: str, target: str) -> bool:
    return target in ALLOWED.get(current, set())


def locked(payment: Payment | str) -> Payment:
    """The payment row, locked until the end of the transaction (two actions never mix)."""
    pk = payment.pk if isinstance(payment, Payment) else payment
    found = Payment.objects.select_for_update().filter(pk=pk).first()
    if found is None:
        raise errors.PaymentNotFound()
    return found


def move(payment: Payment, target: str, *, actor=None, reason: str = "") -> Payment:
    """Changes the status (inside the caller's transaction, row already locked)."""
    if not can_move(payment.status, target):
        raise errors.InvalidTransition(details={"from": payment.status, "to": target})
    before = payment.status
    payment.status = target
    fields = ["status", "updated_at"]
    stamp = TIMESTAMPS[target]  # every reachable status has its date
    setattr(payment, stamp, timezone.now())
    fields.append(stamp)
    if reason:
        payment.end_reason = reason[:40]
        fields.append("end_reason")
    payment.save(update_fields=fields)
    record(
        f"payments.{target}",
        payment,
        actor=actor,
        before={"status": before},
        after={"status": target},
        metadata={"reason": reason} if reason else None,
    )
    listener = _listeners.get(payment.source_type)
    if listener is not None:
        transaction.on_commit(lambda: listener(payment))
    return payment
