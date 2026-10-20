"""What bookings give to the other modules: verified reviews after a done appointment."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from django.utils import formats

from apps.social.eligibility import Transaction

from .models import Appointment


def _transaction(appointment: Appointment) -> Transaction:
    done = appointment.status == Appointment.Status.COMPLETED
    return Transaction(
        kind="booking",
        id=appointment.pk,
        client_id=appointment.client_id,
        pro_id=appointment.pro_id,
        finished_at=(appointment.completed_at or appointment.ends_at) if done else None,
        label=f"{appointment.service.name}, {formats.date_format(appointment.starts_at, 'j F')}",
    )


class BookingEligibility:
    """A done appointment of the client: she can review the pro, the pro can rate her."""

    kind = "booking"

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        found = Appointment.objects.select_related("service").filter(pk=transaction_id).first()
        return _transaction(found) if found and found.client_id else None

    def finished_for_client(self, client_id: uuid.UUID) -> Iterable[Transaction]:
        from apps.accounts.models import User

        from .selectors import claim_guest_appointments

        user = User.objects.filter(pk=client_id).first()
        if user is not None:
            claim_guest_appointments(user)
        rows = Appointment.objects.filter(
            client_id=client_id, status=Appointment.Status.COMPLETED
        ).select_related("service")
        return [_transaction(a) for a in rows[:50]]

    def finished_for_pro(self, pro_id: uuid.UUID) -> Iterable[Transaction]:
        rows = Appointment.objects.filter(
            pro_id=pro_id, status=Appointment.Status.COMPLETED, client__isnull=False
        ).select_related("service")
        return [_transaction(a) for a in rows[:50]]
