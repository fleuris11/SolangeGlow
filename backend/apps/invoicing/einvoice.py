"""Electronic invoices through an approved platform (France, 2026-2027).

The interface is ready; no platform is connected yet (ADR-011): documents stay « not sent ».
A partner is plugged in by writing its class and naming it in EINVOICE_PROVIDER.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string


@dataclass(frozen=True)
class SendResult:
    status: str  # Document.EInvoice
    reference: str = ""


class EInvoiceProvider(Protocol):
    name: str

    def send(self, document) -> SendResult: ...


class NotConnected:
    """No approved platform yet: nothing leaves, the document is kept as it is."""

    name = "not_connected"

    def send(self, document) -> SendResult:
        return SendResult(status="not_sent")


def provider() -> EInvoiceProvider:
    path = getattr(settings, "EINVOICE_PROVIDER", "")
    return import_string(path)() if path else NotConnected()


def is_connected() -> bool:
    return bool(getattr(settings, "EINVOICE_PROVIDER", ""))
