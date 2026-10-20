"""Reading bookings: whose agenda a person manages, a client's no-shows, the agenda."""

from __future__ import annotations

import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.core.selectors import get_setting
from apps.pros.models import ProProfile

from .models import Appointment, AppointmentStep, StaffMember, TimeOff

A = Appointment.Status


def owner_staff(pro: ProProfile) -> StaffMember:
    """The pro herself in her agenda (created the first time)."""
    staff = StaffMember.objects.filter(pro=pro, is_owner=True).first()
    if staff is None:
        staff = StaffMember.objects.create(
            pro=pro, user=pro.user, name=pro.display_name or "Moi", is_owner=True
        )
    return staff


def own_pro(user) -> ProProfile | None:
    try:
        return user.pro_profile
    except (ObjectDoesNotExist, AttributeError):
        return None


def memberships(user):
    """Agendas a collaborator works in (linked by account, or by phone once she signs in)."""
    if user.phone:
        StaffMember.objects.filter(user__isnull=True, phone=user.phone, is_active=True).update(
            user=user
        )
    return StaffMember.objects.filter(user=user, is_active=True, is_owner=False).select_related(
        "pro"
    )


def agenda_access(user, pro_id=None):
    """(pro, staff ids the person may see or None for all) or (None, None)."""
    pro = own_pro(user)
    if pro is not None and (pro_id is None or str(pro.pk) == str(pro_id)):
        return pro, None
    membership = memberships(user)
    if pro_id is not None:
        membership = membership.filter(pro_id=pro_id)
    found = membership.first()
    if found is None:
        return None, None
    return found.pro, {found.pk}


def no_shows(*, user=None, phone: str = "") -> int:
    """No-shows of a client (all pros) over the period of the settings."""
    months = int(get_setting("booking.no_show_window_months", default=12))
    since = timezone.now() - datetime.timedelta(days=30 * months)
    who = Q(pk__in=[])
    if user is not None:
        who |= Q(client=user)
        if user.phone:
            who |= Q(client_phone=str(user.phone))
    if phone:
        who |= Q(client_phone=phone)
    return Appointment.objects.filter(who, status=A.NO_SHOW, starts_at__gte=since).count()


def appointments_between(pro, start, end, *, staff_ids=None):
    rows = (
        Appointment.objects.filter(pro=pro, starts_at__lt=end, ends_at__gt=start)
        .exclude(status__in=[A.EXPIRED])
        .select_related("service", "client", "payment")
        .prefetch_related(
            Prefetch("steps", queryset=AppointmentStep.objects.select_related("staff", "resource"))
        )
        .order_by("starts_at")
    )
    if staff_ids is not None:
        rows = rows.filter(steps__staff_id__in=staff_ids).distinct()
    return rows


def time_off_between(pro, start, end, *, staff_ids=None):
    rows = TimeOff.objects.filter(pro=pro, starts_at__lt=end, ends_at__gt=start)
    if staff_ids is not None:
        rows = rows.filter(Q(staff_id__in=staff_ids) | Q(staff__isnull=True))
    return rows.order_by("starts_at")


def _full(rows):
    return rows.select_related(
        "pro__photo", "pro__country", "service", "payment", "client"
    ).prefetch_related(
        Prefetch("steps", queryset=AppointmentStep.objects.select_related("staff")),
        "options",
        "photos__media",
        "recommendations__product",
    )


def claim_guest_appointments(user) -> int:
    """A guest who signs in with the same (verified) number finds her appointments."""
    if not user.phone or not user.phone_verified_at:
        return 0
    return Appointment.objects.filter(
        client__isnull=True, guest__isnull=False, client_phone=str(user.phone)
    ).update(client=user)


def with_details(rows):
    """Everything an appointment card shows, in a few queries."""
    return _full(rows)


def client_appointments(user):
    claim_guest_appointments(user)
    return _full(Appointment.objects.filter(client=user)).order_by("-starts_at")


def appointment_by_id(appointment_id) -> Appointment:
    return _full(Appointment.objects.all()).get(pk=appointment_id)


def appointment_for(user, appointment_id) -> Appointment | None:
    """The client's own appointment, or one of the agenda she manages."""
    found = (
        Appointment.objects.select_related("pro", "service", "payment", "client", "guest")
        .prefetch_related("steps__staff", "photos__media", "recommendations__product")
        .filter(pk=appointment_id)
        .first()
    )
    if found is None:
        return None
    if found.client_id == user.pk:
        return found
    pro, staff_ids = agenda_access(user, found.pro_id)
    if pro is None:
        return None
    if staff_ids is not None and not found.steps.filter(staff_id__in=staff_ids).exists():
        return None
    return found
