"""What a pro sets up: her people (and their accounts), hours, breaks, time off, blocked
ranges, resources, booking settings; client files, result photos, product advice,
last-minute offers; the iCal export."""

from __future__ import annotations

import datetime
import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.choices import Role
from apps.core.media.models import MediaAsset
from apps.notifications.services import notify
from apps.pros.models import Service

from .. import errors, selectors
from ..models import (
    Appointment,
    AppointmentPhoto,
    BookingSettings,
    ClientRecord,
    LastMinuteAlert,
    LastMinuteOffer,
    Recommendation,
    Resource,
    StaffBreak,
    StaffMember,
    StaffPeriod,
    TimeOff,
)
from . import common

COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
A = Appointment.Status


# --- People of the agenda ------------------------------------------------------------------------


@transaction.atomic
def save_staff(
    pro,
    *,
    staff_id=None,
    name: str,
    color: str = "#C8102E",
    phone: str = "",
    service_ids=None,
    daily_limit: int | None = None,
    own_hours: bool = False,
    is_active: bool = True,
) -> StaffMember:
    selectors.owner_staff(pro)
    name = (name or "").strip()[:80]
    if not name or not COLOR.match(color or ""):
        raise errors.InvalidStaff()
    if staff_id:
        staff = StaffMember.objects.filter(pk=staff_id, pro=pro).first()
        if staff is None:
            raise errors.StaffNotFound()
    else:
        staff = StaffMember(pro=pro, position=StaffMember.objects.filter(pro=pro).count())
    staff.name, staff.color = name, color
    staff.daily_limit = daily_limit if daily_limit else None
    staff.own_hours = bool(own_hours)
    becomes_active = (
        bool(is_active) and not staff.is_owner and (staff._state.adding or not staff.is_active)
    )
    if becomes_active:
        _check_team_size(pro, staff)
    staff.is_active = bool(is_active) or staff.is_owner
    number = common.normalize_phone(phone) if phone else ""
    invite = bool(number) and str(staff.phone or "") != number and not staff.is_owner
    if invite:
        staff.phone = number
        staff.invited_at = timezone.now()
    staff.save()
    if service_ids is not None:
        staff.services.set(Service.objects.filter(pro=pro, pk__in=list(service_ids)))
    if invite:
        _link_account(staff)
    common.changed(pro)
    return staff


def _check_team_size(pro, staff: StaffMember) -> None:
    """The free plan has a few people besides the pro (Glow Pro limit « staff »)."""
    from apps.glowpro import errors as glowpro_errors
    from apps.glowpro import selectors as glowpro

    allowed = glowpro.limit(pro, "staff")
    if allowed is None:
        return
    others = StaffMember.objects.filter(pro=pro, is_owner=False, is_active=True).exclude(
        pk=staff.pk
    )
    if others.count() >= allowed:
        raise glowpro_errors.StaffLimit(details={"limit": allowed})


def _link_account(staff: StaffMember) -> None:
    """A collaborator who already has an account is linked now (else when she signs in)."""
    from apps.accounts.models import User

    user = User.objects.filter(phone=staff.phone, is_active=True).first()
    if user is None:
        return
    staff.user = user
    staff.save(update_fields=["user", "updated_at"])
    if Role.COLLABORATOR not in user.roles:
        user.roles = [*user.roles, Role.COLLABORATOR]
        user.save(update_fields=["roles"])
    transaction.on_commit(
        lambda: notify(user, "booking.invited", {"pro": staff.pro.display_name}, link="/pro/agenda")
    )


def set_hours(pro, staff_id, rows: list[dict], *, kind: str = "periods") -> StaffMember:
    """Replaces the weekly hours (or breaks) of a person: [{weekday, starts_at, ends_at}]."""
    staff = StaffMember.objects.filter(pk=staff_id, pro=pro).first()
    if staff is None:
        raise errors.StaffNotFound()
    model = StaffPeriod if kind == "periods" else StaffBreak
    for row in rows:
        if row["ends_at"] <= row["starts_at"] or not 0 <= int(row["weekday"]) <= 6:
            raise errors.InvalidHours()
    with transaction.atomic():
        model.objects.filter(staff=staff).delete()
        model.objects.bulk_create(
            model(
                staff=staff,
                weekday=int(r["weekday"]),
                starts_at=r["starts_at"],
                ends_at=r["ends_at"],
            )
            for r in rows
        )
    common.changed(pro)
    return staff


def add_time_off(pro, *, staff_id=None, starts_at, ends_at, kind=TimeOff.Kind.ABSENCE, note=""):
    if ends_at <= starts_at:
        raise errors.InvalidHours()
    if staff_id and not StaffMember.objects.filter(pk=staff_id, pro=pro).exists():
        raise errors.StaffNotFound()
    off = TimeOff.objects.create(
        pro=pro,
        staff_id=staff_id or None,
        kind=kind,
        starts_at=starts_at,
        ends_at=ends_at,
        note=(note or "")[:120],
    )
    common.changed(pro)
    return off


def remove_time_off(pro, time_off_id) -> None:
    deleted, _ = TimeOff.objects.filter(pk=time_off_id, pro=pro).delete()
    if not deleted:
        raise errors.InvalidHours()
    common.changed(pro)


def save_resource(pro, *, resource_id=None, name: str, quantity: int = 1) -> Resource:
    name = (name or "").strip()[:60]
    if not name or type(quantity) is not int or quantity < 1:
        raise errors.InvalidStaff()
    resource = (
        Resource.objects.filter(pk=resource_id, pro=pro).first()
        if resource_id
        else Resource(pro=pro)
    )
    if resource is None:
        raise errors.InvalidStaff()
    resource.name, resource.quantity = name, quantity
    resource.save()
    common.changed(pro)
    return resource


def update_settings(pro, **changes) -> BookingSettings:
    settings = BookingSettings.objects.get_or_create(pro=pro)[0]
    for field in (
        "auto_confirm",
        "slot_step_minutes",
        "min_notice_minutes",
        "horizon_days",
        "free_cancel_hours",
        "late_tolerance_minutes",
        "accepts_guests",
    ):
        if field in changes:
            setattr(settings, field, changes[field])
    settings.full_clean()
    settings.save()
    pro._booking_settings = settings
    common.changed(pro)
    return settings


# --- Client files, photos, advice ----------------------------------------------------------------


def record_for(pro, appointment: Appointment) -> ClientRecord:
    if appointment.client_id:
        found, _ = ClientRecord.objects.get_or_create(
            pro=pro, client=appointment.client, defaults={"name": appointment.client_name}
        )
    else:
        found, _ = ClientRecord.objects.get_or_create(
            pro=pro,
            client=None,
            phone=appointment.client_phone,
            defaults={"name": appointment.client_name},
        )
    return found


def update_record(pro, record_id, *, notes=None, preferences=None) -> ClientRecord:
    found = ClientRecord.objects.filter(pk=record_id, pro=pro).first()
    if found is None:
        raise errors.AppointmentNotFound()
    if notes is not None:
        found.notes = notes.strip()[:2000]
    if preferences is not None:
        found.preferences = preferences.strip()[:1000]
    found.save()
    return found


def history_of(record: ClientRecord):
    who = Q(client_id=record.client_id) if record.client_id else Q(client_phone=record.phone)
    return (
        Appointment.objects.filter(who, pro=record.pro)
        .select_related("service")
        .prefetch_related("photos__media")
        .order_by("-starts_at")
    )


def add_photo(pro, appointment: Appointment, media_id, *, owner) -> AppointmentPhoto:
    media = MediaAsset.objects.filter(pk=media_id, owner=owner, purpose="booking_result").first()
    if media is None or appointment.pro_id != pro.pk:
        raise errors.AppointmentNotFound()
    return AppointmentPhoto.objects.create(appointment=appointment, media=media)


def recommend(pro, appointment: Appointment, product_id, *, note: str = "") -> Recommendation:
    from apps.shop.selectors import on_sale

    if appointment.pro_id != pro.pk or appointment.status != A.COMPLETED:
        raise errors.InvalidStep()
    product = on_sale().filter(pk=product_id, pro=pro).first()
    if product is None:
        raise errors.ProductNotFound()
    advice, created = Recommendation.objects.get_or_create(
        appointment=appointment, product=product, defaults={"note": (note or "")[:300]}
    )
    if created:
        common.tell_client(appointment, "booking.advice", {"product": product.title})
    return advice


# --- Last minute ---------------------------------------------------------------------------------


def set_last_minute(pro, *, percent_off: int, window_hours: int, is_active: bool):
    offer, _ = LastMinuteOffer.objects.get_or_create(pro=pro)
    offer.percent_off, offer.window_hours = percent_off, window_hours
    was_active = offer.is_active
    offer.is_active = bool(is_active)
    offer.full_clean()
    offer.save()
    pro.last_minute = offer
    common.changed(pro)
    if offer.is_active and not was_active:
        transaction.on_commit(lambda: announce_last_minute(offer))
    return offer


def announce_last_minute(offer: LastMinuteOffer) -> int:
    """Clients near the pro (her followers and past clients of her city), once a day each."""
    from apps.accounts.models import User

    pro = offer.pro
    today = timezone.localdate()
    from apps.social.models import Follow

    followers = Follow.objects.filter(followed=pro.user).values("follower_id")
    came = Appointment.objects.filter(pro=pro, client__isnull=False).values("client_id")
    nearby = User.objects.filter(Q(pk__in=followers) | Q(pk__in=came), is_active=True).exclude(
        pk=pro.user_id
    )
    if pro.city:
        # Followers of the same city, and every client who already came.
        nearby = nearby.filter(Q(city__iexact=pro.city) | Q(pk__in=came))
    sent = 0
    for user in nearby[:500]:
        _, created = LastMinuteAlert.objects.get_or_create(
            user=user, sent_on=today, defaults={"pro": pro}
        )
        if not created:
            continue
        notify(
            user,
            "booking.last_minute",
            {"pro": pro.display_name, "percent": offer.percent_off},
            link=f"/{pro.slug}/rdv",
        )
        sent += 1
    offer.announced_at = timezone.now()
    offer.save(update_fields=["announced_at", "updated_at"])
    record("booking.last_minute", offer, metadata={"sent": sent})
    return sent


# --- iCal ----------------------------------------------------------------------------------------


def _ics_text(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def ical(pro, *, staff_id=None) -> str:
    """The agenda for Google Calendar or the iPhone (from 30 days ago to the horizon)."""
    start = timezone.now() - datetime.timedelta(days=30)
    end = timezone.now() + datetime.timedelta(days=120)
    rows = selectors.appointments_between(
        pro, start, end, staff_ids={staff_id} if staff_id else None
    ).filter(status__in=[*Appointment.BLOCKING, A.COMPLETED])
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Solange Glow//Agenda//FR",
        f"X-WR-CALNAME:{_ics_text(pro.display_name)}",
    ]
    for appointment in rows:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{appointment.pk}@solangeglow.com",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{appointment.starts_at.astimezone(datetime.UTC):%Y%m%dT%H%M%SZ}",
            f"DTEND:{appointment.ends_at.astimezone(datetime.UTC):%Y%m%dT%H%M%SZ}",
            f"SUMMARY:{_ics_text(f'{appointment.service.name} - {appointment.client_name}')}",
            f"DESCRIPTION:{_ics_text(appointment.reference)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
