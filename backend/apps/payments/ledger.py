"""Double-entry ledger: every movement of money is a balanced, immutable entry.

- An entry has lines; each line is a debit or a credit on one account.
- Debits equal credits, all lines are in the same currency (no implicit conversion).
- An entry is written once: its unique key makes a replay harmless.
- Balances are computed from the lines, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Sum

from .models import JournalEntry, JournalLine, LedgerAccount

Kind = LedgerAccount.Kind


class LedgerError(ValueError):
    """An entry that would break the ledger (unbalanced, mixed currencies, empty…)."""


@dataclass(frozen=True)
class Line:
    account: LedgerAccount
    debit: int = 0
    credit: int = 0


def account(kind: str, currency: str, *, owner=None, provider: str = "") -> LedgerAccount:
    """The account, created the first time it is needed."""
    found, _ = LedgerAccount.objects.get_or_create(
        kind=kind, currency=currency.upper(), owner=owner, provider=provider
    )
    return found


def debit(acc: LedgerAccount, amount: int) -> Line:
    return Line(acc, debit=amount)


def credit(acc: LedgerAccount, amount: int) -> Line:
    return Line(acc, credit=amount)


def _check(lines: list[Line]) -> str:
    kept = [line for line in lines if line.debit or line.credit]
    if not kept:
        raise LedgerError("empty entry")
    currencies = {line.account.currency for line in kept}
    if len(currencies) != 1:
        raise LedgerError("one currency per entry")
    for line in kept:
        if not all(type(value) is int for value in (line.debit, line.credit)):
            raise LedgerError("amounts are integers in the smallest unit")
        if line.debit < 0 or line.credit < 0 or (line.debit and line.credit):
            raise LedgerError("a line is a positive debit or a positive credit")
    if sum(line.debit for line in kept) != sum(line.credit for line in kept):
        raise LedgerError("debits and credits differ")
    return currencies.pop()


def post(
    kind: str,
    key: str,
    lines: list[Line],
    *,
    payment=None,
    refund=None,
    payout=None,
    actor=None,
    description: str = "",
) -> JournalEntry:
    """Writes a balanced entry once. With an existing key, returns the entry already written."""
    existing = JournalEntry.objects.filter(idempotency_key=key).first()
    if existing is not None:
        return existing
    currency = _check(lines)
    try:
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                kind=kind,
                idempotency_key=key,
                currency=currency,
                description=description[:255],
                payment=payment,
                refund=refund,
                payout=payout,
                actor=actor,
            )
            JournalLine.objects.bulk_create(
                JournalLine(
                    entry=entry,
                    account=line.account,
                    debit_minor=line.debit,
                    credit_minor=line.credit,
                )
                for line in lines
                if line.debit or line.credit
            )
    except IntegrityError:  # the same key written at the same moment
        return JournalEntry.objects.get(idempotency_key=key)
    return entry


def balance(acc: LedgerAccount, *, payment=None) -> int:
    """Balance on the natural side of the account (positive when it holds money)."""
    lines = JournalLine.objects.filter(account=acc)
    if payment is not None:
        lines = lines.filter(entry__payment=payment)
    totals = lines.aggregate(debit=Sum("debit_minor"), credit=Sum("credit_minor"))
    debits, credits = totals["debit"] or 0, totals["credit"] or 0
    return debits - credits if acc.debit_normal else credits - debits


def balance_of(kind: str, currency: str, *, owner=None, provider: str | None = None) -> int:
    """Total of every account of this kind and currency (all providers when not given)."""
    accounts = LedgerAccount.objects.filter(kind=kind, currency=currency.upper())
    if owner is not None:
        accounts = accounts.filter(owner=owner)
    if provider is not None:
        accounts = accounts.filter(provider=provider)
    totals = JournalLine.objects.filter(account__in=accounts).aggregate(
        debit=Sum("debit_minor"), credit=Sum("credit_minor")
    )
    debits, credits = totals["debit"] or 0, totals["credit"] or 0
    return debits - credits if kind in LedgerAccount.DEBIT_NORMAL else credits - debits


def is_balanced() -> bool:
    """The whole ledger, per currency: debits equal credits (checked by the reconciliation)."""
    rows = (
        JournalLine.objects.values("account__currency")
        .annotate(debit=Sum("debit_minor"), credit=Sum("credit_minor"))
        .values_list("debit", "credit")
    )
    return all(debits == credits for debits, credits in rows)
