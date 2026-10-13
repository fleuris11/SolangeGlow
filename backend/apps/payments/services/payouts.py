"""The seller takes her available money: payout methods, requests, provider answers.

Ledger: request   Dr seller available / Cr payouts in progress
        paid      Dr payouts in progress / Cr provider cash
        failed    Dr payouts in progress / Cr seller available (the money comes back)
"""

from __future__ import annotations

import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.core import crypto
from apps.core.audit.services import record
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from .. import errors, ledger
from ..ledger import credit, debit
from ..models import LedgerAccount, Payout, PayoutMethod
from ..providers import ProviderError, ProviderNotConfigured, get_provider, provider_for
from .payments import _country_of, money

Kind = LedgerAccount.Kind
P = Payout.Status


def _mask(kind: str, details: dict) -> str:
    if kind == PayoutMethod.Kind.MOBILE_MONEY:
        number = str(details.get("number", ""))
        return f"{details.get('operator', '')} •••• {number[-4:]}".strip()
    if kind == PayoutMethod.Kind.STRIPE:
        return f"Stripe •••• {str(details.get('account', ''))[-4:]}"
    return str(details.get("label", "Test"))[:80]


def save_payout_method(seller, *, currency: str, kind: str, details: dict) -> PayoutMethod:
    method, _ = PayoutMethod.objects.update_or_create(
        seller=seller,
        currency=currency.upper(),
        defaults={
            "kind": kind,
            "details_secret": crypto.encrypt(json.dumps(details)),
            "display": _mask(kind, details),
        },
    )
    record("payments.payout_method_saved", method, actor=seller)
    return method


def _check_identity(seller) -> None:
    from apps.pros.selectors import can_collect_payments

    try:
        pro = seller.pro_profile
    except ObjectDoesNotExist:
        return
    if not can_collect_payments(pro):
        raise errors.IdentityNeeded()


def request_payout(seller, *, amount_minor: int, currency: str) -> Payout:
    currency = currency.upper()
    _check_identity(seller)
    minimums = get_setting("payments.payout_minimum", default={"XOF": 5000, "EUR": 1000}) or {}
    minimum = int(minimums.get(currency, 0))
    if type(amount_minor) is not int or amount_minor < max(minimum, 1):
        raise errors.BelowMinimum(details={"minimum": money(minimum, currency, seller)})
    method = PayoutMethod.objects.filter(seller=seller, currency=currency).first()
    if method is None:
        raise errors.NoPayoutMethod()
    if method.kind == PayoutMethod.Kind.FAKE:
        provider_name = "fake"
    else:
        try:
            provider_name = provider_for(_country_of(seller)).name
        except ProviderNotConfigured as exc:
            raise errors.PaymentsUnavailable() from exc
    with transaction.atomic():
        available = ledger.account(Kind.SELLER_AVAILABLE, currency, owner=seller)
        # One request at a time per seller and currency.
        LedgerAccount.objects.select_for_update().get(pk=available.pk)
        balance = ledger.balance(available)
        if amount_minor > balance:
            raise errors.NotEnoughMoney(details={"available": money(balance, currency, seller)})
        payout = Payout.objects.create(
            seller=seller,
            amount_minor=amount_minor,
            currency=currency,
            provider=provider_name,
            destination=method.display,
        )
        ledger.post(
            "payout.requested",
            f"payout:{payout.pk}:requested",
            [
                debit(available, amount_minor),
                credit(ledger.account(Kind.PAYOUTS_IN_TRANSIT, currency), amount_minor),
            ],
            payout=payout,
            actor=seller,
        )
        record("payments.payout_requested", payout, actor=seller)
        from ..tasks import run_payout

        transaction.on_commit(lambda: run_payout.delay(str(payout.pk)))
    return payout


def execute_payout(payout_id) -> Payout:
    payout = Payout.objects.select_related("seller").get(pk=payout_id)
    if payout.status != P.REQUESTED:
        return payout
    method = PayoutMethod.objects.filter(seller=payout.seller, currency=payout.currency).first()
    try:
        if method is None:
            raise ProviderNotConfigured("no payout method")
        details = json.loads(crypto.decrypt(method.details_secret) or "{}")
        provider = get_provider(payout.provider)
        result = provider.payout(payout, details)
    except ProviderNotConfigured as exc:
        return payout_failed(payout, error=str(exc))
    except ProviderError as exc:
        payout.error = str(exc)[:255]
        payout.save(update_fields=["error", "updated_at"])
        return payout
    payout.provider_reference = result.reference
    payout.status = P.PROCESSING
    payout.save(update_fields=["provider_reference", "status", "updated_at"])
    if result.status == "paid":
        return payout_paid(payout)
    answer_later = getattr(provider, "answer_later", None)  # the test provider
    if answer_later is not None:
        answer_later("payout", result.reference, payout.amount_minor, payout.currency)
    return payout


@transaction.atomic
def payout_paid(payout: Payout) -> Payout:
    payout = Payout.objects.select_for_update().get(pk=payout.pk)
    if payout.status in (P.PAID, P.FAILED):
        return payout
    ledger.post(
        "payout.paid",
        f"payout:{payout.pk}:paid",
        [
            debit(ledger.account(Kind.PAYOUTS_IN_TRANSIT, payout.currency), payout.amount_minor),
            credit(
                ledger.account(Kind.PROVIDER_CASH, payout.currency, provider=payout.provider),
                payout.amount_minor,
            ),
        ],
        payout=payout,
    )
    payout.status, payout.paid_at, payout.error = P.PAID, timezone.now(), ""
    payout.save(update_fields=["status", "paid_at", "error", "updated_at"])
    record("payments.payout_paid", payout)
    amount = money(payout.amount_minor, payout.currency, payout.seller)
    transaction.on_commit(
        lambda: notify(payout.seller, "payouts.paid", {"amount": amount}, link="/pro/wallet")
    )
    return payout


@transaction.atomic
def payout_failed(payout: Payout, *, error: str) -> Payout:
    payout = Payout.objects.select_for_update().get(pk=payout.pk)
    if payout.status in (P.PAID, P.FAILED):
        return payout
    ledger.post(
        "payout.failed",
        f"payout:{payout.pk}:failed",
        [
            debit(ledger.account(Kind.PAYOUTS_IN_TRANSIT, payout.currency), payout.amount_minor),
            credit(
                ledger.account(Kind.SELLER_AVAILABLE, payout.currency, owner=payout.seller),
                payout.amount_minor,
            ),
        ],
        payout=payout,
    )
    payout.status, payout.error = P.FAILED, error[:255]
    payout.save(update_fields=["status", "error", "updated_at"])
    record("payments.payout_failed", payout, metadata={"error": payout.error})
    amount = money(payout.amount_minor, payout.currency, payout.seller)
    transaction.on_commit(
        lambda: notify(payout.seller, "payouts.failed", {"amount": amount}, link="/pro/wallet")
    )
    return payout
