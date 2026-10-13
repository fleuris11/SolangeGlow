"""Provider news (webhooks): signature checked, each event processed once.

An expected refusal (wrong amount, unknown reference) is kept as « failed » or « ignored »
for the finance team and answered 200, so the provider stops sending it. An unexpected
error rolls everything back (nothing recorded): the provider sends it again later.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.core.errors import DomainError

from ..models import Payment, Payout, Refund, WebhookEvent
from ..providers import EventKind, get_provider
from . import payments as payment_services
from . import payouts as payout_services
from . import refunds as refund_services

W = WebhookEvent.Status


def _dispatch(provider: str, event) -> str:
    kind = event.kind
    if kind in (EventKind.PAYMENT_SUCCEEDED, EventKind.PAYMENT_FAILED, EventKind.PAYMENT_CANCELLED):
        payment = Payment.objects.filter(
            provider=provider, provider_reference=event.reference
        ).first()
        if payment is None:
            return W.IGNORED
        if kind == EventKind.PAYMENT_SUCCEEDED:
            payment_services.mark_paid(
                payment,
                amount_minor=event.amount_minor,
                currency=event.currency or payment.currency,
                fee_minor=event.fee_minor,
                key=f"{provider}:{event.event_id}",
            )
        else:
            reason = "failed" if kind == EventKind.PAYMENT_FAILED else "abandoned"
            payment_services.mark_not_paid(payment, reason=reason)
        return W.PROCESSED
    if kind in (EventKind.REFUND_SUCCEEDED, EventKind.REFUND_FAILED):
        refund = Refund.objects.filter(provider_reference=event.reference).first()
        if refund is None:
            return W.IGNORED
        if kind == EventKind.REFUND_SUCCEEDED:
            refund_services.refund_succeeded(refund)
        else:
            refund_services.refund_failed(refund, error="provider")
        return W.PROCESSED
    if kind in (EventKind.PAYOUT_PAID, EventKind.PAYOUT_FAILED):
        payout = Payout.objects.filter(provider_reference=event.reference).first()
        if payout is None:
            return W.IGNORED
        if kind == EventKind.PAYOUT_PAID:
            payout_services.payout_paid(payout)
        else:
            payout_services.payout_failed(payout, error="provider")
        return W.PROCESSED
    return W.IGNORED


def handle(provider_name: str, headers, body: bytes) -> list[WebhookEvent]:
    """Raises ProviderNotConfigured (unknown or off) or InvalidSignature (not from them)."""
    provider = get_provider(provider_name)
    events = provider.parse_webhook(headers, body)
    handled = []
    for event in events:
        if WebhookEvent.objects.filter(provider=provider.name, event_id=event.event_id).exists():
            continue  # already received
        try:
            with transaction.atomic():
                stored = WebhookEvent.objects.create(
                    provider=provider.name,
                    event_id=event.event_id,
                    kind=event.kind,
                    payload=event.raw,
                    status=W.PROCESSED,
                )
                try:
                    with transaction.atomic():
                        stored.status = _dispatch(provider.name, event)
                except DomainError as exc:
                    stored.status, stored.error = W.FAILED, f"{exc.code}: {exc.text()}"[:255]
                stored.save(update_fields=["status", "error", "updated_at"])
        except IntegrityError:  # the same event at the same moment
            continue
        handled.append(stored)
    return handled
