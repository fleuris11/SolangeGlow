"""What every payment provider offers (ADR-007): checkout, refund, payout, webhooks."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from typing import Protocol

from apps.core.providers.base import ProviderError, ProviderNotConfigured

__all__ = [
    "Checkout",
    "Event",
    "EventKind",
    "InvalidSignature",
    "PaymentProvider",
    "PayoutResult",
    "ProviderError",
    "ProviderNotConfigured",
    "RefundResult",
    "Transaction",
    "sign",
    "verify_timestamped",
]


class InvalidSignature(Exception):
    """A webhook that does not come from the provider (or too old)."""


class EventKind:
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_CANCELLED = "payment.cancelled"
    REFUND_SUCCEEDED = "refund.succeeded"
    REFUND_FAILED = "refund.failed"
    PAYOUT_PAID = "payout.paid"
    PAYOUT_FAILED = "payout.failed"
    OTHER = "other"


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    reference: str  # provider reference of the payment, refund or payout
    amount_minor: int | None = None
    currency: str = ""
    fee_minor: int = 0
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Checkout:
    reference: str
    url: str


@dataclass(frozen=True)
class RefundResult:
    reference: str
    status: str  # "pending", "succeeded" or "manual" (to do by hand at the provider)


@dataclass(frozen=True)
class PayoutResult:
    reference: str
    status: str  # "pending" or "paid"


@dataclass(frozen=True)
class Transaction:
    """A line of the provider's statement, for the reconciliation."""

    reference: str
    amount_minor: int
    currency: str
    fee_minor: int = 0


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, payment, *, return_url: str) -> Checkout: ...

    def refund(self, payment, refund) -> RefundResult: ...

    def payout(self, payout, details: dict) -> PayoutResult: ...

    def parse_webhook(self, headers: dict, body: bytes) -> list[Event]: ...

    def transactions(self, since, until) -> list[Transaction]: ...


def sign(secret: str, timestamp: int, body: bytes) -> str:
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify_timestamped(
    header: str, body: bytes, secret: str, *, scheme: str, tolerance: int = 300
) -> None:
    """Checks a « t=<time>,<scheme>=<hex> » header (Stripe, FedaPay and our fake provider)."""
    parts = {}
    for item in (header or "").split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts["t"][0])
    except (KeyError, ValueError) as exc:
        raise InvalidSignature("no timestamp") from exc
    if abs(time.time() - timestamp) > tolerance:
        raise InvalidSignature("too old")
    expected = sign(secret, timestamp, body)
    if not any(hmac.compare_digest(expected, given) for given in parts.get(scheme, [])):
        raise InvalidSignature("bad signature")
