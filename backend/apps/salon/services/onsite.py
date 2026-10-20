"""Money the pro takes herself at the salon (cash, Mobile Money, her card terminal).

It never goes through the platform, so it is not in the ledger of the secure payment: it is
kept for her dashboard and her receipts. This is not a certified till (NF525): recording
cash is only offered in the countries of the setting `salon.cash_countries`.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record

from .. import errors, terminal
from ..models import OnSitePayment
from . import common

M = OnSitePayment.Method


def methods_for(pro) -> list[str]:
    """Ways of paying the pro can record in her country."""
    countries = common.setting("salon.cash_countries", pro, ["BJ"])
    code = pro.country.code if pro.country_id else ""
    methods = [M.CASH, M.MOMO] if code in countries else []
    if terminal.is_configured(code):
        methods.append(M.CARD)
    return methods


@transaction.atomic
def record_payment(
    pro,
    *,
    amount_minor: int,
    method: str,
    actor,
    label: str = "",
    appointment=None,
    client_record=None,
    reference: str = "",
) -> OnSitePayment:
    if type(amount_minor) is not int or amount_minor <= 0 or method not in M.values:
        raise errors.InvalidPayment()
    if method == M.CARD and not terminal.is_configured(pro.country.code if pro.country_id else ""):
        raise errors.TerminalNotConfigured()
    if method not in methods_for(pro):
        raise errors.MethodNotAvailable()
    if appointment is not None:
        label = label or appointment.service.name
        if client_record is None:
            from apps.booking.services.agenda import record_for

            client_record = record_for(pro, appointment)
    payment = OnSitePayment.objects.create(
        pro=pro,
        appointment=appointment,
        record=client_record,
        label=(label or "—")[:120],
        amount_minor=amount_minor,
        currency=pro.currency or "XOF",
        method=method,
        reference=(reference or "")[:60],
        recorded_by=actor,
    )
    record("salon.on_site_payment", payment, actor=actor, metadata={"amount": amount_minor})
    return payment


@transaction.atomic
def cancel_payment(payment: OnSitePayment, *, actor, reason: str) -> OnSitePayment:
    """A mistake: the payment stays in the history, marked cancelled (and its receipt
    cancelled by a credit note)."""
    payment = OnSitePayment.objects.select_for_update().get(pk=payment.pk)
    if payment.cancelled_at:
        raise errors.AlreadyCancelled()
    payment.cancelled_at = timezone.now()
    payment.cancel_reason = (reason or "")[:120]
    payment.save(update_fields=["cancelled_at", "cancel_reason", "updated_at"])
    from apps.invoicing import services as invoicing

    receipt = invoicing.for_source("salon_on_site", payment.pk, "receipt")
    if receipt is not None:
        invoicing.credit(receipt, actor=actor, reason=reason)
    record("salon.on_site_payment_cancelled", payment, actor=actor)
    return payment
