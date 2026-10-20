"""Waiting list: a place frees up, the first client waiting for that day gets it kept for
her for a while (30 minutes by default); without an answer it goes to the next one."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.pros.hours import zone_of

from .. import availability, errors
from ..models import Appointment, WaitlistEntry
from . import appointments, common

W = WaitlistEntry.Status
A = Appointment.Status


def join(
    pro,
    service_id,
    day: datetime.date,
    *,
    user=None,
    guest_name: str = "",
    guest_phone: str = "",
    from_time=None,
    to_time=None,
    staff_id=None,
) -> WaitlistEntry:
    service = appointments._service(pro, service_id)
    appointments._staff(pro, staff_id, service)
    if from_time and to_time and to_time <= from_time:
        raise errors.InvalidHours()
    guest = None
    if user is None:
        phone = common.normalize_phone(guest_phone)
        name = (guest_name or "").strip()[:150]
        if not phone or not name:
            raise errors.GuestDetailsNeeded()
        guest = common.guest_for(name, phone)
        mine = WaitlistEntry.objects.filter(guest__phone=phone)
    else:
        mine = WaitlistEntry.objects.filter(client=user)
    if mine.filter(pro=pro, service=service, day=day, status=W.WAITING).exists():
        raise errors.AlreadyInList()
    return WaitlistEntry.objects.create(
        pro=pro,
        service=service,
        staff_id=staff_id,
        day=day,
        from_time=from_time,
        to_time=to_time,
        client=user,
        guest=guest,
    )


def leave(entry: WaitlistEntry) -> None:
    if entry.status in (W.WAITING, W.OFFERED):
        if entry.offer_id:
            appointments._close(entry.offer, A.EXPIRED, by=Appointment.CancelledBy.CLIENT)
        entry.status = W.CANCELLED
        entry.save(update_fields=["status", "updated_at"])


def _matching_slot(entry: WaitlistEntry):
    zone = zone_of(entry.pro)
    for slot in availability.day_slots(
        entry.pro, entry.service, entry.day, staff_id=entry.staff_id
    ):
        local = slot.start.astimezone(zone).time()
        if entry.from_time and local < entry.from_time:
            continue
        if entry.to_time and local > entry.to_time:
            continue
        return slot
    return None


def offer_freed_place(pro, day: datetime.date) -> WaitlistEntry | None:
    """The first waiting client who fits a free place of the day gets it kept for her."""
    if WaitlistEntry.objects.filter(pro=pro, day=day, status=W.OFFERED).exists():
        return None  # one offer at a time for a day: the next comes after her answer
    minutes = int(common.setting("booking.waitlist_answer_minutes", pro, 30))
    for entry in WaitlistEntry.objects.filter(pro=pro, day=day, status=W.WAITING).select_related(
        "service", "client", "guest", "pro"
    ):
        slot = _matching_slot(entry)
        if slot is None:
            continue
        try:
            with transaction.atomic():
                held = _hold(entry, slot)
                entry.status = W.OFFERED
                entry.offer = held
                entry.offer_expires_at = timezone.now() + datetime.timedelta(minutes=minutes)
                entry.save(update_fields=["status", "offer", "offer_expires_at", "updated_at"])
                common.tell_client(held, "booking.waitlist_offer", {"minutes": minutes})
        except DomainError:  # changed meanwhile (taken, deposit without account…): next one
            continue
        return entry
    return None


def _hold(entry: WaitlistEntry, slot) -> Appointment:
    guest = entry.guest
    return appointments.book(
        entry.pro,
        entry.service_id,
        slot.start,
        user=entry.client,
        guest_name=guest.first_name if guest else "",
        guest_phone=str(guest.phone) if guest else "",
        staff_id=entry.staff_id,
        source=Appointment.Source.WAITLIST,
        status=A.HELD,
    )


@transaction.atomic
def accept(entry: WaitlistEntry, *, user=None) -> Appointment:
    entry = (
        WaitlistEntry.objects.select_for_update(of=("self",))
        .select_related("offer", "pro")
        .get(pk=entry.pk)
    )
    if entry.status != W.OFFERED or entry.offer is None:
        raise errors.InvalidStep()
    if entry.offer_expires_at and entry.offer_expires_at < timezone.now():
        raise errors.OfferExpired()
    held = appointments._locked(entry.offer)
    if held.deposit_minor and held.client_id:
        held.status = A.AWAITING_DEPOSIT
        held.save(update_fields=["status", "updated_at"])
        appointments._start_deposit(held, held.client)
    else:
        held.status = A.CONFIRMED
        held.confirmed_at = timezone.now()
        held.save(update_fields=["status", "confirmed_at", "updated_at"])
        common.tell_pro(held, "booking.new")
    common.set_blocking(held)
    common.changed(held.pro)
    entry.status = W.BOOKED
    entry.save(update_fields=["status", "updated_at"])
    record("booking.waitlist_booked", held, actor=user)
    return held


def expire_offers(now=None) -> int:
    """Offers without answer: the place goes back, then to the next client of the list."""
    now = now or timezone.now()
    count = 0
    for entry in WaitlistEntry.objects.filter(
        status=W.OFFERED, offer_expires_at__lte=now
    ).select_related("offer", "pro"):
        with transaction.atomic():
            if entry.offer and entry.offer.status == A.HELD:
                appointments._close(entry.offer, A.EXPIRED, by=Appointment.CancelledBy.SYSTEM)
            entry.status = W.EXPIRED
            entry.save(update_fields=["status", "updated_at"])
        offer_freed_place(entry.pro, entry.day)
        count += 1
    return count
