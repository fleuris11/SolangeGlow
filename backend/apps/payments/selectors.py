"""Reading money: a seller's wallet, payments of a person, the finance dashboard."""

from __future__ import annotations

from django.db.models import Q, Sum

from . import ledger
from .models import Dispute, LedgerAccount, Payment, Payout, Refund

Kind = LedgerAccount.Kind
S = Payment.Status
ACTIVE = (S.HELD, S.SHIPPED, S.DISPUTED)


def currencies_of(seller) -> list[str]:
    found = set(
        LedgerAccount.objects.filter(owner=seller).values_list("currency", flat=True)
    ) | set(Payment.objects.filter(seller=seller).values_list("currency", flat=True))
    return sorted(found)


def wallet(seller, currency: str) -> dict:
    """Pending (held for her orders), available, being paid out, already paid out."""
    paid = Payout.objects.filter(
        seller=seller, currency=currency, status=Payout.Status.PAID
    ).aggregate(total=Sum("amount_minor"))["total"]
    in_progress = Payout.objects.filter(
        seller=seller,
        currency=currency,
        status__in=[Payout.Status.REQUESTED, Payout.Status.PROCESSING],
    ).aggregate(total=Sum("amount_minor"))["total"]
    return {
        "currency": currency,
        "pending_minor": ledger.balance_of(Kind.SELLER_PENDING, currency, owner=seller),
        "available_minor": ledger.balance_of(Kind.SELLER_AVAILABLE, currency, owner=seller),
        "in_progress_minor": in_progress or 0,
        "paid_out_minor": paid or 0,
    }


def wallet_history(seller, currency: str, *, limit: int = 50):
    """Lines of her accounts, newest first, with what each one was about."""
    from .models import JournalLine

    return (
        JournalLine.objects.filter(
            account__owner=seller,
            account__currency=currency,
            account__kind__in=[Kind.SELLER_PENDING, Kind.SELLER_AVAILABLE],
        )
        .select_related("entry", "entry__payment", "account")
        .order_by("-entry__created_at", "-id")[:limit]
    )


def payments_of(user, *, role: str):
    field = "seller" if role == "seller" else "buyer"
    return (
        Payment.objects.filter(**{field: user})
        .exclude(status=S.PENDING_PAYMENT, checkout_url="")
        .select_related("buyer", "seller")
        .order_by("-created_at")
    )


def payment_for(user, payment_id) -> Payment | None:
    """A payment she takes part in (as client or seller)."""
    return (
        Payment.objects.filter(pk=payment_id)
        .filter(Q(buyer=user) | Q(seller=user))
        .select_related("buyer", "seller", "delivery_proof")
        .first()
    )


def dealt_together(user, other) -> bool:
    """A paid order between them: numbers and links are normal now (messaging)."""
    return Payment.objects.filter(
        Q(buyer=user, seller=other) | Q(buyer=other, seller=user),
        status__in=[*ACTIVE, S.RELEASED, S.PARTIALLY_REFUNDED],
    ).exists()


def dashboard() -> list[dict]:
    """Per currency: held money, owed to sellers, in progress, revenues, open disputes."""
    currencies = sorted(set(LedgerAccount.objects.values_list("currency", flat=True)))
    rows = []
    for currency in currencies:
        rows.append(
            {
                "currency": currency,
                "cash": ledger.balance_of(Kind.PROVIDER_CASH, currency),
                "escrow": ledger.balance_of(Kind.SELLER_PENDING, currency)
                + ledger.balance_of(Kind.FEES_PENDING, currency),
                "sellers_available": ledger.balance_of(Kind.SELLER_AVAILABLE, currency),
                "payouts_in_progress": ledger.balance_of(Kind.PAYOUTS_IN_TRANSIT, currency),
                "refunds_in_progress": ledger.balance_of(Kind.REFUNDS_IN_TRANSIT, currency),
                "commissions": ledger.balance_of(Kind.COMMISSION_REVENUE, currency),
                "buyer_protection": ledger.balance_of(Kind.FEE_REVENUE, currency),
                "payment_fees": ledger.balance_of(Kind.PROVIDER_FEES, currency),
                "open_disputes": Dispute.objects.filter(
                    status=Dispute.Status.OPEN, payment__currency=currency
                ).count(),
                "refunds_to_do": Refund.objects.filter(
                    currency=currency,
                    status__in=[Refund.Status.MANUAL, Refund.Status.FAILED],
                ).count(),
            }
        )
    return rows
