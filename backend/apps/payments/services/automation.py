"""What happens by itself, with the deadlines of the admin settings (Celery Beat).

Every step can run twice without effect twice: it only picks payments still in the
expected state, and each move locks the payment.
"""

from __future__ import annotations

import datetime
import logging

from django.db import transaction
from django.utils import timezone

from apps.core.errors import DomainError
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from ..models import Dispute, Payment, Payout, Refund
from . import disputes as dispute_services
from . import payments as payment_services
from .common import S

logger = logging.getLogger("solangeglow.payments")
day = datetime.timedelta(days=1)


def _setting(key: str, payment: Payment, default):
    return get_setting(key, country=payment.country or None, default=default)


def _safely(step, payment) -> bool:
    """One payment that cannot move (changed meanwhile) never stops the others."""
    try:
        step(payment)
    except DomainError:
        logger.info("Skipped %s for payment %s", step.__name__, payment.pk)
        return False
    return True


def expire_unpaid(now=None) -> int:
    now = now or timezone.now()
    due = Payment.objects.filter(status=S.PENDING_PAYMENT, expires_at__lte=now)
    return sum(
        _safely(lambda p: payment_services.mark_not_paid(p, reason="expired"), p) for p in due
    )


def remind_shipping(now=None) -> int:
    now = now or timezone.now()
    count = 0
    with transaction.atomic():
        waiting = (
            Payment.objects.select_for_update(skip_locked=True)
            .filter(status=S.HELD, ship_reminded_at__isnull=True)
            .exclude(delivery_mode=Payment.Delivery.SERVICE)
        )
        for payment in waiting:
            days = int(_setting("escrow.ship_deadline_days", payment, 3))
            hours = int(_setting("escrow.ship_reminder_hours", payment, 24))
            deadline = payment.paid_at + days * day
            if now < deadline - datetime.timedelta(hours=hours):
                continue
            payment.ship_reminded_at = now
            payment.save(update_fields=["ship_reminded_at", "updated_at"])
            transaction.on_commit(
                lambda p=payment, d=deadline: notify(
                    p.seller,
                    "payments.ship_reminder",
                    {"reference": p.reference, "deadline": d.date().isoformat()},
                    link=f"/payments/{p.pk}",
                )
            )
            count += 1
    return count


def cancel_unshipped(now=None) -> int:
    now = now or timezone.now()
    due = [
        p
        for p in Payment.objects.filter(status=S.HELD).exclude(
            delivery_mode=Payment.Delivery.SERVICE
        )
        if p.paid_at + int(_setting("escrow.ship_deadline_days", p, 3)) * day <= now
    ]
    return sum(
        _safely(lambda p: payment_services.refund_full(p, reason="not_shipped"), p) for p in due
    )


def remind_release(now=None) -> int:
    """Delivered without a code: « did you get it? give the code or tell us »."""
    now = now or timezone.now()
    count = 0
    with transaction.atomic():
        delivered = Payment.objects.select_for_update(skip_locked=True).filter(
            status=S.SHIPPED, delivered_at__isnull=False
        )
        for payment in delivered:
            days = list(_setting("escrow.release_reminder_days", payment, [2, 5]))
            sent = payment.release_reminders
            if sent >= len(days) or now < payment.delivered_at + int(days[sent]) * day:
                continue
            payment.release_reminders = sent + 1
            payment.save(update_fields=["release_reminders", "updated_at"])
            transaction.on_commit(
                lambda p=payment: notify(
                    p.buyer,
                    "payments.release_reminder",
                    {"reference": p.reference},
                    link=f"/payments/{p.pk}",
                )
            )
            count += 1
    return count


def auto_release(now=None) -> int:
    """Delivered (or appointment passed) and nothing said: the seller gets her money."""
    now = now or timezone.now()
    due = []
    for payment in Payment.objects.filter(status=S.SHIPPED, delivered_at__isnull=False):
        days = int(_setting("escrow.auto_release_days", payment, 7))
        if payment.delivered_at + days * day <= now:
            due.append(payment)
    for payment in Payment.objects.filter(
        status=S.HELD, delivery_mode=Payment.Delivery.SERVICE, service_at__isnull=False
    ):
        days = int(_setting("escrow.auto_release_days", payment, 7))
        if payment.service_at + days * day <= now:
            due.append(payment)
    return sum(_safely(lambda p: payment_services.release(p, reason="automatic"), p) for p in due)


def auto_dispute(now=None) -> int:
    """No code and no proof of delivery long after the expected date: a dispute opens."""
    now = now or timezone.now()
    due = []
    for payment in Payment.objects.filter(
        status=S.SHIPPED, delivered_at__isnull=True, expected_delivery_at__isnull=False
    ):
        days = int(_setting("escrow.auto_dispute_days", payment, 7))
        if payment.expected_delivery_at + days * day <= now:
            due.append(payment)
    return sum(
        _safely(lambda p: dispute_services.open_dispute(p, reason=Dispute.Reason.NO_PROOF), p)
        for p in due
    )


def retry_stuck(now=None) -> dict:
    """Refunds and payouts the provider could not take (network): try again."""
    from ..tasks import run_payout, run_refund

    now = now or timezone.now()
    since = now - datetime.timedelta(minutes=10)
    refunds = Refund.objects.filter(
        status=Refund.Status.PENDING, provider_reference="", updated_at__lte=since
    )
    payouts = Payout.objects.filter(status=Payout.Status.REQUESTED, updated_at__lte=since)
    for refund in refunds:
        run_refund.delay(str(refund.pk))
    for payout in payouts:
        run_payout.delay(str(payout.pk))
    return {"refunds": len(refunds), "payouts": len(payouts)}


def run_all(now=None) -> dict:
    now = now or timezone.now()
    return {
        "expired": expire_unpaid(now),
        "ship_reminders": remind_shipping(now),
        "not_shipped": cancel_unshipped(now),
        "release_reminders": remind_release(now),
        "released": auto_release(now),
        "disputes": auto_dispute(now),
        "deadlines": dispute_services.follow_deadlines(now),
        "retried": retry_stuck(now),
    }
