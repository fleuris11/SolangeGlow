"""Card payment on the pro's phone (Tap to Pay through Stripe Terminal).

The interface is ready; no terminal is configured yet (keys missing): the method is not
offered. A provider is plugged in by naming its class in TERMINAL_PROVIDER.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from apps.core.providers.base import ProviderNotConfigured


@dataclass(frozen=True)
class TerminalSession:
    """What the phone needs to take a card (a connection token and the amount)."""

    reference: str
    client_secret: str


class TerminalProvider(Protocol):
    def start(self, *, amount_minor: int, currency: str, description: str) -> TerminalSession: ...


class StripeTerminal:
    """Stripe Terminal (Tap to Pay on Android and iPhone). Needs STRIPE_SECRET_KEY."""

    def __init__(self):
        if not getattr(settings, "STRIPE_SECRET_KEY", ""):
            raise ProviderNotConfigured("Stripe Terminal")

    def start(self, *, amount_minor: int, currency: str, description: str) -> TerminalSession:
        raise ProviderNotConfigured("Stripe Terminal")  # connected with the live keys (V3)


def provider() -> TerminalProvider:
    path = getattr(settings, "TERMINAL_PROVIDER", "")
    if not path:
        raise ProviderNotConfigured("terminal")
    return import_string(path)()


def is_configured(country_code: str = "") -> bool:
    try:
        provider()
    except ProviderNotConfigured:
        return False
    return True
