"""Conversions: a purchase (money paid) or an appointment done after a click on an ad."""

from __future__ import annotations

from apps.payments.models import Payment, Purpose

from .common import setting
from .tracking import convert

# What the platform sells to the pros themselves never counts as a conversion of an ad.
DEFAULT_IGNORED = [Purpose.BOOST, Purpose.SUBSCRIPTION]


def on_payment_moved(payment: Payment) -> None:
    if payment.status != Payment.Status.HELD:
        return
    if payment.purpose in (setting("ads.conversion_ignored_purposes", DEFAULT_IGNORED) or []):
        return
    convert(payment.buyer, f"payment:{payment.pk}")


def on_appointment_completed(appointment) -> None:
    # An appointment with a deposit already counted with its payment.
    if appointment.client_id and not appointment.payment_id:
        convert(appointment.client, f"booking:{appointment.pk}")
