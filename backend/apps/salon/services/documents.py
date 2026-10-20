"""The invoice of a done appointment, the receipt of a payment taken at the salon, the
invoice of a package or a gift card: issued once, then always the same document."""

from __future__ import annotations

from django.utils.translation import gettext as _

from apps.booking.models import Appointment
from apps.invoicing import services as invoicing
from apps.invoicing.models import Document
from apps.payments.models import Payment

from .. import errors
from ..models import ClientPackage, GiftCard, OnSitePayment

K = Document.Kind


def _buyer(client_record=None, user=None, name="") -> dict:
    if client_record is not None:
        name = client_record.name
        user = user or client_record.client
    return {"buyer_name": name or "—", "buyer_user": user}


def _paid_with(appointment: Appointment) -> str:
    means = [p.get_method_display() for p in appointment.on_site_payments.filter(cancelled_at=None)]
    if appointment.payment_id and appointment.payment.status in (
        Payment.Status.HELD,
        Payment.Status.RELEASED,
    ):
        means.append(
            _("Online deposit %(reference)s") % {"reference": appointment.payment.reference}
        )
    if appointment.gift_card_uses.exists():
        means.append(_("Gift card"))
    return ", ".join(dict.fromkeys(means))[:60]


def for_appointment(appointment: Appointment) -> Document:
    from apps.booking.services.agenda import record_for

    if appointment.status != Appointment.Status.COMPLETED or appointment.price_minor in (None, 0):
        raise errors.NotFound()
    lines = [
        {"label": appointment.service.name, "quantity": 1, "unit_minor": appointment.price_minor}
    ]
    return invoicing.issue_once(
        invoicing.issuer_for(appointment.pro),
        K.INVOICE,
        source_type="booking",
        source_id=appointment.pk,
        lines=lines,
        currency=appointment.currency,
        paid_with=_paid_with(appointment),
        **_buyer(record_for(appointment.pro, appointment)),
    )


def for_on_site(payment: OnSitePayment) -> Document:
    if payment.cancelled_at:
        raise errors.AlreadyCancelled()
    return invoicing.issue_once(
        invoicing.issuer_for(payment.pro),
        K.RECEIPT,
        source_type="salon_on_site",
        source_id=payment.pk,
        lines=[{"label": payment.label, "quantity": 1, "unit_minor": payment.amount_minor}],
        currency=payment.currency,
        paid_with=" ".join(filter(None, (payment.get_method_display(), payment.reference)))[:60],
        **_buyer(payment.record),
    )


def for_package(sold: ClientPackage) -> Document:
    return invoicing.issue_once(
        invoicing.issuer_for(sold.pro),
        K.INVOICE,
        source_type="salon_package",
        source_id=sold.pk,
        lines=[
            {
                "label": _("%(name)s (%(count)s sessions)")
                % {"name": sold.package.name, "count": sold.sessions_total},
                "quantity": 1,
                "unit_minor": sold.price_minor,
            }
        ],
        currency=sold.currency,
        **_buyer(sold.record),
    )


def for_gift_card(card: GiftCard) -> Document:
    if card.status == GiftCard.Status.WAITING:
        raise errors.NotFound()
    return invoicing.issue_once(
        invoicing.issuer_for(card.pro),
        K.RECEIPT,
        source_type="salon_gift_card",
        source_id=card.pk,
        lines=[
            {
                "label": _("Gift card %(code)s") % {"code": card.code},
                "quantity": 1,
                "unit_minor": card.amount_minor,
            }
        ],
        currency=card.currency,
        paid_with=card.payment.reference if card.payment_id else "",
        **_buyer(user=card.buyer, name=card.from_name),
    )
