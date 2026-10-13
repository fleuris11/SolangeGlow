"""The test provider: a payment page of the web app lets the person choose « success »,
« failure » or « give up »; refunds and payouts succeed. Every answer comes back as a
signed webhook, exactly like a real provider. Only when `PAYMENTS_FAKE_ENABLED` is on.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid

from django.conf import settings

from .base import (
    Checkout,
    Event,
    EventKind,
    PayoutResult,
    ProviderNotConfigured,
    RefundResult,
    Transaction,
    sign,
    verify_timestamped,
)

HEADER = "X-Fake-Signature"


def secret() -> str:
    return hashlib.sha256(f"solangeglow-fake-provider|{settings.SECRET_KEY}".encode()).hexdigest()


def signed_event(kind: str, reference: str, amount_minor: int | None, currency: str) -> tuple:
    """Body and headers of a webhook as the fake provider would send it."""
    body = json.dumps(
        {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": kind,
            "reference": reference,
            "amount": amount_minor,
            "currency": currency,
        }
    ).encode()
    timestamp = int(time.time())
    return body, {HEADER: f"t={timestamp},v1={sign(secret(), timestamp, body)}"}


class FakeProvider:
    name = "fake"

    def __init__(self):
        if not settings.PAYMENTS_FAKE_ENABLED:
            raise ProviderNotConfigured("Fake payments are off")

    def create_checkout(self, payment, *, return_url: str) -> Checkout:
        reference = f"fake_{payment.pk.hex}"
        return Checkout(reference=reference, url=f"{settings.SITE_URL}/pay/test/{payment.pk}")

    def refund(self, payment, refund) -> RefundResult:
        return RefundResult(reference=f"fake_refund_{refund.pk.hex}", status="pending")

    def payout(self, payout, details: dict) -> PayoutResult:
        return PayoutResult(reference=f"fake_payout_{payout.pk.hex}", status="pending")

    def answer_later(self, kind: str, reference: str, amount_minor: int, currency: str) -> None:
        """Called once our reference is saved: the « provider » confirms by webhook."""
        from ..tasks import send_fake_event

        event = EventKind.REFUND_SUCCEEDED if kind == "refund" else EventKind.PAYOUT_PAID
        send_fake_event.delay(event, reference, amount_minor, currency)

    def parse_webhook(self, headers: dict, body: bytes) -> list[Event]:
        verify_timestamped(headers.get(HEADER, ""), body, secret(), scheme="v1")
        data = json.loads(body)
        return [
            Event(
                event_id=data["id"],
                kind=data["type"],
                reference=data["reference"],
                amount_minor=data.get("amount"),
                currency=data.get("currency") or "",
                raw=data,
            )
        ]

    def transactions(self, since, until) -> list[Transaction]:
        """Our own records: the test provider has no statement of its own."""
        from ..models import Payment

        paid = Payment.objects.filter(
            provider=self.name, paid_at__gte=since, paid_at__lt=until
        ).exclude(provider_reference="")
        return [Transaction(p.provider_reference, p.total_minor, p.currency) for p in paid]
