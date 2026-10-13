"""FedaPay (Benin: MTN MoMo, Moov Money, Celtiis Cash, cards). Off without keys.

API (docs.fedapay.com): POST /v1/transactions, POST /v1/transactions/{id}/token (payment
link), POST /v1/payouts then PUT /v1/payouts/start (Mobile Money payouts). Webhooks carry
« X-FEDAPAY-SIGNATURE: t=<time>,s=<hmac sha256 of "t.body"> ». FedaPay has no refund API:
refunds are marked « to do by hand » in the admin. The platform collects then pays the
seller out: this setup is to be validated with FedaPay and a lawyer (specification).
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

URLS = {"sandbox": "https://sandbox-api.fedapay.com/v1", "live": "https://api.fedapay.com/v1"}
EVENTS = {
    "transaction.approved": EventKind.PAYMENT_SUCCEEDED,
    "transaction.declined": EventKind.PAYMENT_FAILED,
    "transaction.canceled": EventKind.PAYMENT_CANCELLED,
    "payout.sent": EventKind.PAYOUT_PAID,
    "payout.failed": EventKind.PAYOUT_FAILED,
}


def _unwrap(data: dict, name: str) -> dict:
    """FedaPay wraps objects as {"v1/transaction": {...}}; accept both shapes."""
    return data.get(f"v1/{name}", data) if isinstance(data, dict) else {}


class FedaPayProvider:
    name = "fedapay"

    def __init__(self):
        if not settings.FEDAPAY_SECRET_KEY:
            raise ProviderNotConfigured("FedaPay")
        self.base = URLS.get(settings.FEDAPAY_ENVIRONMENT, URLS["sandbox"])
        self.headers = {
            "Authorization": f"Bearer {settings.FEDAPAY_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def _call(self, method: str, path: str, payload) -> dict | list:
        try:
            response = httpx.request(
                method, f"{self.base}{path}", json=payload, headers=self.headers, timeout=20
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"FedaPay unreachable: {exc}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"FedaPay {response.status_code}: {response.text[:200]}")
        return response.json()

    def create_checkout(self, payment, *, return_url: str) -> Checkout:
        buyer = payment.buyer
        transaction = _unwrap(
            self._call(
                "POST",
                "/transactions",
                {
                    "description": payment.description[:200],
                    "amount": payment.total_minor,
                    "currency": {"iso": payment.currency},
                    "callback_url": return_url,
                    "customer": {
                        "firstname": buyer.first_name or "Client",
                        "lastname": buyer.last_name or "Solange Glow",
                        **({"email": buyer.email} if buyer.email else {}),
                    },
                    "custom_metadata": {"payment": str(payment.pk)},
                },
            ),
            "transaction",
        )
        token = self._call("POST", f"/transactions/{transaction['id']}/token", None)
        return Checkout(reference=str(transaction["id"]), url=token["url"])

    def refund(self, payment, refund) -> RefundResult:
        return RefundResult(reference="", status="manual")

    def payout(self, payout, details: dict) -> PayoutResult:
        phone = {"number": details["number"], "country": details.get("country", "BJ")}
        created = _unwrap(
            self._call(
                "POST",
                "/payouts",
                {
                    "amount": payout.amount_minor,
                    "currency": {"iso": payout.currency},
                    "mode": details.get("mode", "mobile_money"),
                    "customer": {
                        "firstname": details.get("firstname", ""),
                        "lastname": details.get("lastname", ""),
                        "phone_number": phone,
                    },
                },
            ),
            "payout",
        )
        self._call("PUT", "/payouts/start", [{"id": created["id"], "phone_number": phone}])
        return PayoutResult(reference=str(created["id"]), status="pending")

    def parse_webhook(self, headers: dict, body: bytes) -> list[Event]:
        verify_timestamped(
            headers.get("X-Fedapay-Signature", "") or headers.get("X-FEDAPAY-SIGNATURE", ""),
            body,
            settings.FEDAPAY_WEBHOOK_SECRET,
            scheme="s",
        )
        data = json.loads(body)
        entity = data.get("entity") or data.get("object") or {}
        currency = entity.get("currency") or {}
        name = data.get("name", "")
        return [
            Event(
                event_id=str(data.get("id") or f"{name}:{entity.get('id')}"),
                kind=EVENTS.get(name, EventKind.OTHER),
                reference=str(entity.get("id", "")),
                amount_minor=entity.get("amount"),
                currency=currency.get("iso", "") if isinstance(currency, dict) else "",
                fee_minor=int(entity.get("fees") or 0),
                raw=data,
            )
        ]

    def transactions(self, since, until) -> list[Transaction]:
        data = self._call("GET", "/transactions?per_page=500", None)
        rows = data.get("v1/transactions", []) if isinstance(data, dict) else []
        return [
            Transaction(str(row["id"]), int(row["amount"]), "XOF", int(row.get("fees") or 0))
            for row in rows
            if row.get("status") == "approved"
        ]
