"""Stripe Connect (France: cards, Apple Pay, Google Pay). Off without keys.

« Separate charges and transfers »: the platform charges the client (Checkout Session,
transfer_group = our reference), keeps the money, then transfers the seller's part to her
connected account at the release (POST /v1/transfers). Stripe allows transfers up to 90 days
after the charge in France: our deadlines stay far below. Webhooks carry
« Stripe-Signature: t=<time>,v1=<hmac sha256 of "t.body"> ».
"""

from __future__ import annotations

import json

import httpx
from django.conf import settings

from .base import (
    Checkout,
    Event,
    EventKind,
    PayoutResult,
    ProviderError,
    ProviderNotConfigured,
    RefundResult,
    Transaction,
    verify_timestamped,
)

API = "https://api.stripe.com/v1"


class StripeConnectProvider:
    name = "stripe"

    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            raise ProviderNotConfigured("Stripe")

    def _call(self, method: str, path: str, data: dict | None = None) -> dict:
        try:
            response = httpx.request(
                method,
                f"{API}{path}",
                data=data,
                auth=(settings.STRIPE_SECRET_KEY, ""),
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Stripe unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"Stripe {response.status_code}: {response.text[:200]}")
        return response.json()

    def create_checkout(self, payment, *, return_url: str) -> Checkout:
        session = self._call(
            "POST",
            "/checkout/sessions",
            {
                "mode": "payment",
                "line_items[0][quantity]": 1,
                "line_items[0][price_data][currency]": payment.currency.lower(),
                "line_items[0][price_data][unit_amount]": payment.total_minor,
                "line_items[0][price_data][product_data][name]": payment.description[:200],
                "success_url": return_url,
                "cancel_url": return_url,
                "client_reference_id": str(payment.pk),
                "metadata[payment]": str(payment.pk),
                "payment_intent_data[transfer_group]": payment.reference,
            },
        )
        return Checkout(reference=session["id"], url=session["url"])

    def refund(self, payment, refund) -> RefundResult:
        session = self._call("GET", f"/checkout/sessions/{payment.provider_reference}")
        created = self._call(
            "POST",
            "/refunds",
            {
                "payment_intent": session["payment_intent"],
                "amount": refund.amount_minor,
                "metadata[refund]": str(refund.pk),
            },
        )
        status = "succeeded" if created.get("status") == "succeeded" else "pending"
        return RefundResult(reference=created["id"], status=status)

    def payout(self, payout, details: dict) -> PayoutResult:
        transfer = self._call(
            "POST",
            "/transfers",
            {
                "amount": payout.amount_minor,
                "currency": payout.currency.lower(),
                "destination": details["account"],
                "metadata[payout]": str(payout.pk),
            },
        )
        return PayoutResult(reference=transfer["id"], status="paid")

    def parse_webhook(self, headers: dict, body: bytes) -> list[Event]:
        verify_timestamped(
            headers.get("Stripe-Signature", ""), body, settings.STRIPE_WEBHOOK_SECRET, scheme="v1"
        )
        data = json.loads(body)
        kind, obj = data.get("type", ""), data.get("data", {}).get("object", {})
        mapped = EventKind.OTHER
        paid = kind == "checkout.session.completed" and obj.get("payment_status") == "paid"
        if paid or kind == "checkout.session.async_payment_succeeded":
            mapped = EventKind.PAYMENT_SUCCEEDED
        elif kind == "checkout.session.async_payment_failed":
            mapped = EventKind.PAYMENT_FAILED
        elif kind == "checkout.session.expired":
            mapped = EventKind.PAYMENT_CANCELLED
        elif kind in ("refund.updated", "refund.created"):
            mapped = {
                "succeeded": EventKind.REFUND_SUCCEEDED,
                "failed": EventKind.REFUND_FAILED,
            }.get(obj.get("status"), EventKind.OTHER)
        amount = obj.get("amount_total", obj.get("amount"))
        return [
            Event(
                event_id=data.get("id", ""),
                kind=mapped,
                reference=obj.get("id", ""),
                amount_minor=amount,
                currency=(obj.get("currency") or "").upper(),
                raw=data,
            )
        ]

    def transactions(self, since, until) -> list[Transaction]:
        data = self._call(
            "GET",
            "/balance_transactions?type=charge&limit=100"
            f"&created[gte]={int(since.timestamp())}&created[lt]={int(until.timestamp())}",
        )
        return [
            Transaction(
                row.get("source", ""), row["amount"], row["currency"].upper(), row.get("fee", 0)
            )
            for row in data.get("data", [])
        ]
