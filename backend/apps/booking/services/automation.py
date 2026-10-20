"""What happens by itself (Celery Beat every 5 minutes): reminders, requests and proposals
without answer, waiting-list offers that expire, unpaid group shares, the reviews."""

from __future__ import annotations

import datetime
import logging

from django.db import transaction
from django.utils import timezone

from apps.core.errors import DomainError

from ..models import Appointment
from . import appointments, common, groups, waitlist

logger = logging.getLogger("solangeglow.booking")
A = Appointment.Status


def send_reminders(now=None) -> int:
    """« Tomorrow at 10:30 » then « in 2 hours »: each reminder once (settings, in hours)."""
    now = now or timezone.now()
    sent = 0
    upcoming = Appointment.objects.filter(
        status=A.CONFIRMED,
        starts_at__gt=now,
        starts_at__lte=now + datetime.timedelta(days=3),
    ).select_related("pro", "service", "client")
    for appointment in upcoming:
        hours = sorted(
            int(h) for h in common.setting("booking.reminder_hours", appointment.pro, [24, 2])
        )
        due = [
            h
            for h in hours
            if appointment.starts_at - datetime.timedelta(hours=h) <= now
            and h not in appointment.reminders_sent
        ]
        if not due:
            continue
        with transaction.atomic():
            # Only the closest one: no « tomorrow » message two hours before.
            appointment.reminders_sent = sorted({*appointment.reminders_sent, *due})
            appointment.save(update_fields=["reminders_sent", "updated_at"])
            common.tell_client(appointment, "booking.reminder", {"hours": min(due)})
        sent += 1
    return sent


def expire_answers(now=None) -> int:
    """Requests the pro did not answer, proposals the client did not answer: cancelled."""
    now = now or timezone.now()
    count = 0
    for appointment in Appointment.objects.filter(
        status__in=[A.PENDING, A.PROPOSED], answer_due_at__lte=now
    ):
        try:
            appointments.cancel(appointment, by=Appointment.CancelledBy.SYSTEM)
            count += 1
        except DomainError:
            logger.info("Skipped expiry of %s", appointment.pk)
    return count


def run_all(now=None) -> dict:
    now = now or timezone.now()
    return {
        "reminders": send_reminders(now),
        "answers": expire_answers(now),
        "waitlist": waitlist.expire_offers(now),
        "groups": groups.close_unpaid(now),
    }
