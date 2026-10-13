"""Refunds sent through the provider; FedaPay ones are done by hand (no refund API).

Ledger when the provider confirms: Dr refunds in progress / Cr provider cash.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record

from .. import ledger
from ..ledger import credit, debit
from ..models import LedgerAccount, Refund
from ..providers import ProviderError, ProviderNotConfigured, get_provider

Kind = LedgerAccount.Kind
R = Refund.Status


def start_refund(refund_id) -> Refund:
    """Asks the provider; a network failure leaves it pending for the next try."""
    refund = Refund.objects.select_related("payment").get(pk=refund_id)
    if refund.status != R.PENDING or refund.provider_reference:
        return refund
    try:
        provider = get_provider(refund.payment.provider)
        result = provider.refund(refund.payment, refund)
    except ProviderNotConfigured as exc:
        refund.status, refund.error = R.MANUAL, str(exc)[:255]
        refund.save(update_fields=["status", "error", "updated_at"])
        return refund
    except ProviderError as exc:
        refund.error = str(exc)[:255]
        refund.save(update_fields=["error", "updated_at"])
        return refund
    refund.provider_reference = result.reference
    if result.status == "manual":
        refund.status = R.MANUAL
    refund.save(update_fields=["provider_reference", "status", "updated_at"])
    if result.status == "succeeded":
        return refund_succeeded(refund)
    answer_later = getattr(provider, "answer_later", None)  # the test provider
    if answer_later is not None:
        answer_later("refund", result.reference, refund.amount_minor, refund.currency)
    return refund


@transaction.atomic
def refund_succeeded(refund: Refund, *, actor=None) -> Refund:
    refund = Refund.objects.select_for_update().select_related("payment").get(pk=refund.pk)
    if refund.status == R.SUCCEEDED:
        return refund
    payment = refund.payment
    ledger.post(
        "refund.succeeded",
        f"refund:{refund.pk}:succeeded",
        [
            debit(ledger.account(Kind.REFUNDS_IN_TRANSIT, refund.currency), refund.amount_minor),
            credit(
                ledger.account(Kind.PROVIDER_CASH, refund.currency, provider=payment.provider),
                refund.amount_minor,
            ),
        ],
        payment=payment,
        refund=refund,
        actor=actor,
    )
    refund.status = R.SUCCEEDED
    refund.completed_at = timezone.now()
    refund.error = ""
    refund.save(update_fields=["status", "completed_at", "error", "updated_at"])
    record("payments.refund_succeeded", refund, actor=actor)
    return refund


@transaction.atomic
def refund_failed(refund: Refund, *, error: str) -> Refund:
    """The money is still owed (refunds in progress): the finance team sees it in red."""
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if refund.status in (R.SUCCEEDED, R.FAILED):
        return refund
    refund.status, refund.error = R.FAILED, error[:255]
    refund.save(update_fields=["status", "error", "updated_at"])
    record("payments.refund_failed", refund, metadata={"error": refund.error})
    return refund


def mark_done_by_hand(refund: Refund, *, actor) -> Refund:
    """Done in the provider's dashboard (FedaPay, or after a failure): close it."""
    return refund_succeeded(refund, actor=actor)
