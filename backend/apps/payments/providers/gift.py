"""Money of a gift (Diaspora gifts, ADR-014): an offered service, product or Glow gift card
pays a payment in FCFA without any provider page. The euros were paid before, on their
own payment; this « provider » is the platform itself.

A refund goes back onto the gift: the module of the gifts registers the callback that
credits it (`on_refund`). Nothing is ever paid out through it.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import Checkout, Event, PayoutResult, ProviderError, RefundResult, Transaction

NAME = "gift"

_refund_callbacks: list[Callable] = []


def on_refund(callback: Callable) -> None:
    """callback(payment, refund): puts the refunded money back onto the gift (idempotent)."""
    if callback not in _refund_callbacks:
        _refund_callbacks.append(callback)


class GiftProvider:
    name = NAME

    def create_checkout(self, payment, *, return_url: str) -> Checkout:
        raise ProviderError("A gift pays at once, without a page")

    def refund(self, payment, refund) -> RefundResult:
        if not _refund_callbacks:
            raise ProviderError("No module takes the money of a gift back")
        for callback in list(_refund_callbacks):
            callback(payment, refund)
        return RefundResult(reference=f"gift_refund_{refund.pk.hex}", status="succeeded")

    def payout(self, payout, details: dict) -> PayoutResult:
        raise ProviderError("Nothing is paid out from a gift")

    def parse_webhook(self, headers: dict, body: bytes) -> list[Event]:
        return []

    def transactions(self, since, until) -> list[Transaction]:
        return []
