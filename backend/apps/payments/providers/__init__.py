"""Payment providers behind one interface (ADR-007).

`provider_for(country)` reads the setting `payments.providers` (country → provider). A
provider without keys raises `ProviderNotConfigured`; the test provider replaces it only
where `PAYMENTS_FAKE_ENABLED` is on (development, tests, never production).
"""

from __future__ import annotations

from django.conf import settings

from apps.core.selectors import get_setting

from .base import (
    Checkout,
    Event,
    EventKind,
    InvalidSignature,
    PaymentProvider,
    PayoutResult,
    ProviderError,
    ProviderNotConfigured,
    RefundResult,
    Transaction,
)
from .fake import FakeProvider
from .fedapay import FedaPayProvider
from .stripe import StripeConnectProvider

PROVIDERS = {
    "fake": FakeProvider,
    "fedapay": FedaPayProvider,
    "stripe": StripeConnectProvider,
}

__all__ = [
    "PROVIDERS",
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
    "get_provider",
    "provider_for",
]


def get_provider(name: str) -> PaymentProvider:
    try:
        return PROVIDERS[name]()
    except KeyError as exc:
        raise ProviderNotConfigured(f"Unknown provider {name}") from exc


def provider_for(country: str) -> PaymentProvider:
    choices = get_setting("payments.providers", default={"BJ": "fedapay", "FR": "stripe"}) or {}
    name = choices.get(country) or choices.get("*") or "fake"
    try:
        return get_provider(name)
    except ProviderNotConfigured:
        if settings.PAYMENTS_FAKE_ENABLED:
            return FakeProvider()
        raise
