"""Daily check: the provider's statement against the payments counted in the ledger."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from ..models import Payment, ReconciliationItem, ReconciliationRun
from ..providers import get_provider

I = ReconciliationItem.Kind  # noqa: E741


@transaction.atomic
def reconcile(provider_name: str, *, since=None, until=None) -> ReconciliationRun:
    until = until or timezone.now()
    since = since or until - datetime.timedelta(days=1)
    provider = get_provider(provider_name)
    statement = {row.reference: row for row in provider.transactions(since, until)}
    counted = {
        p.provider_reference: p
        for p in Payment.objects.filter(
            provider=provider.name, paid_at__gte=since, paid_at__lt=until
        ).exclude(provider_reference="")
    }
    run = ReconciliationRun.objects.create(
        provider=provider.name, period_start=since, period_end=until, checked=len(statement)
    )
    items = []
    for reference, row in statement.items():
        payment = counted.get(reference)
        if payment is None:
            items.append(
                ReconciliationItem(
                    run=run,
                    kind=I.MISSING_IN_LEDGER,
                    reference=reference,
                    actual_minor=row.amount_minor,
                    currency=row.currency,
                )
            )
        elif payment.total_minor != row.amount_minor or payment.currency != row.currency:
            items.append(
                ReconciliationItem(
                    run=run,
                    kind=I.AMOUNT_MISMATCH,
                    reference=reference,
                    expected_minor=payment.total_minor,
                    actual_minor=row.amount_minor,
                    currency=payment.currency,
                )
            )
    for reference, payment in counted.items():
        if reference not in statement:
            items.append(
                ReconciliationItem(
                    run=run,
                    kind=I.MISSING_AT_PROVIDER,
                    reference=reference,
                    expected_minor=payment.total_minor,
                    currency=payment.currency,
                )
            )
    ReconciliationItem.objects.bulk_create(items)
    run.discrepancies = len(items)
    run.save(update_fields=["discrepancies", "updated_at"])
    return run
