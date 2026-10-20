"""Group booking (a bride and her bridesmaids): one place per person, at the same time when
there are enough people in the salon, otherwise one after the other. Each person pays her
share of the deposit with the group link; unpaid shares are released after the deadline
(the organiser can pay them)."""

from __future__ import annotations

import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.audit.services import record

from .. import availability, errors
from ..models import Appointment, GroupBooking
from . import appointments, common

A = Appointment.Status
G = GroupBooking.Status


@transaction.atomic
def create_group(
    organizer, pro, service_id, start: datetime.datetime, size: int, *, title="", option_ids=()
) -> GroupBooking:
    maximum = int(common.setting("booking.group_max", pro, 8))
    if type(size) is not int or not 2 <= size <= maximum:
        raise errors.InvalidGroup(details={"max": maximum})
    if not pro.is_published:
        raise errors.ProNotFound()
    if organizer.pk == pro.user_id:
        raise errors.CannotBookYourself()
    service = appointments._service(pro, service_id)
    appointments._check_time(pro, start)
    plans = availability.group_plan(pro, service, start, size, option_ids)
    if plans is None:
        raise errors.GroupDoesNotFit()
    price = appointments.price_of(service, [])
    deposit = appointments.deposit_of(service, price)
    hours = int(common.setting("booking.group_pay_hours", pro, 24))
    group = GroupBooking.objects.create(
        pro=pro,
        organizer=organizer,
        title=(title or "").strip()[:80],
        status=G.COLLECTING if deposit else G.CONFIRMED,
        pay_by=timezone.now() + datetime.timedelta(hours=hours) if deposit else None,
    )
    for index, slot in enumerate(plans):
        first = index == 0
        appointment = Appointment.objects.create(
            reference=common.new_reference(),
            pro=pro,
            service=service,
            client=organizer if first else None,
            client_name=(organizer.first_name if first else f"{organizer.first_name} +{index}"),
            client_phone=str(organizer.phone or ""),
            starts_at=slot.start,
            ends_at=slot.end,
            status=A.AWAITING_DEPOSIT if deposit else A.CONFIRMED,
            source=Appointment.Source.GROUP,
            price_minor=price,
            currency=service.currency,
            deposit_minor=deposit,
            group=group,
            confirmed_at=None if deposit else timezone.now(),
        )
        try:
            with transaction.atomic():
                common.write_steps(appointment, slot)
        except IntegrityError as exc:
            raise errors.SlotTaken() from exc
    common.changed(pro)
    record("booking.group_created", group, actor=organizer)
    first = group.appointments.order_by("starts_at", "created_at").first()
    common.tell_pro(first, "booking.group", {"size": size})
    return group


def claim_share(group: GroupBooking, user, appointment_id=None) -> Appointment:
    """A participant (or the organiser for the rest) takes a share: its deposit to pay."""
    if group.status != G.COLLECTING:
        raise errors.InvalidStep()
    shares = group.appointments.filter(status=A.AWAITING_DEPOSIT, payment__isnull=True)
    if appointment_id:
        shares = shares.filter(pk=appointment_id)
    elif group.organizer_id != user.pk:
        shares = shares.filter(client__isnull=True)
    with transaction.atomic():
        share = shares.select_for_update().order_by("starts_at", "created_at").first()
        if share is None:
            raise errors.InvalidStep()
        if share.client_id is None:
            share.client = user
            share.client_name = user.first_name or share.client_name
            share.client_phone = str(user.phone or "")
            share.save(update_fields=["client", "client_name", "client_phone", "updated_at"])
        appointments._start_deposit(share, user)
    return share


def check_group(group: GroupBooking) -> GroupBooking:
    group.refresh_from_db()
    if (
        group.status == G.COLLECTING
        and not group.appointments.filter(status=A.AWAITING_DEPOSIT).exists()
    ):
        group.status = G.CONFIRMED
        group.save(update_fields=["status", "updated_at"])
    return group


def close_unpaid(now=None) -> int:
    """After the deadline: unpaid places are released, the group keeps the paid ones."""
    now = now or timezone.now()
    count = 0
    for group in GroupBooking.objects.filter(status=G.COLLECTING, pay_by__lte=now):
        with transaction.atomic():
            for share in group.appointments.filter(status=A.AWAITING_DEPOSIT):
                appointments._give_back_deposit(share, "group_unpaid")
                appointments._close(share, A.EXPIRED, by=Appointment.CancelledBy.SYSTEM)
            kept = group.appointments.filter(status=A.CONFIRMED).exists()
            group.status = G.CONFIRMED if kept else G.CANCELLED
            group.save(update_fields=["status", "updated_at"])
        count += 1
    return count
