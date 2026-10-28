"""The life of an appointment: booking (client, guest or by phone), the pro's answer
(accept, decline, propose another time), cancellation and lateness rules, moving, done,
no-show, and the deposit through the secure payment (module 5)."""

from __future__ import annotations

import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose
from apps.pros.hours import zone_of
from apps.pros.models import ProProfile, Service, ServiceOption

from .. import availability, errors, selectors
from ..models import Appointment, BookingSettings, ClientRecord, StaffMember
from . import common

A = Appointment.Status
PS = Payment.Status
SOURCE = "booking"


# --- Prices and deposits -------------------------------------------------------------------------


def price_of(service: Service, options, discount_percent: int = 0) -> int | None:
    if service.price_minor is None:
        return None
    total = service.price_minor + sum(o.price_minor for o in options)
    if discount_percent:
        total = total - (total * discount_percent * 2 + 100) // 200
    return total


def deposit_of(service: Service, price: int | None, *, forced_percent: int = 0) -> int:
    """The service's deposit, or the deposit imposed after too many no-shows."""
    amount = 0
    if service.deposit_kind == "amount":
        amount = service.deposit_value
    elif service.deposit_kind == "percent" and price:
        amount = (price * min(service.deposit_value, 100) * 2 + 100) // 200
    if forced_percent and price:
        amount = max(amount, (price * forced_percent * 2 + 100) // 200)
    if price is not None:
        amount = min(amount, price)
    return amount


def forced_deposit_percent(pro, *, user=None, phone: str = "") -> int:
    threshold = int(common.setting("booking.no_show_threshold", pro, 2))
    if threshold and selectors.no_shows(user=user, phone=phone) >= threshold:
        return int(common.setting("booking.no_show_deposit_percent", pro, 30))
    return 0


# --- Booking --------------------------------------------------------------------------------------


def _service(pro: ProProfile, service_id) -> Service:
    service = (
        Service.objects.filter(pk=service_id, pro=pro, is_active=True, archived_at__isnull=True)
        .prefetch_related("steps", "options")
        .first()
    )
    if service is None:
        raise errors.ServiceNotFound()
    return service


def _staff(pro, staff_id, service: Service):
    if not staff_id:
        return None
    staff = StaffMember.objects.filter(pk=staff_id, pro=pro, is_active=True).first()
    if staff is None:
        raise errors.StaffNotFound()
    allowed = set(staff.services.values_list("pk", flat=True))
    if allowed and service.pk not in allowed:
        raise errors.StaffNotFound()
    return staff


def _check_time(pro, start: datetime.datetime) -> None:
    notice = availability.min_notice(pro)
    if start < timezone.now() + notice:
        raise errors.TooSoon(details={"minutes": int(notice.total_seconds() // 60)})
    days = availability.horizon(pro)
    last = (timezone.now().astimezone(zone_of(pro)) + datetime.timedelta(days=days)).date()
    if start.astimezone(zone_of(pro)).date() > last:
        raise errors.TooFar(details={"days": days})


def _record_client(appointment: Appointment) -> None:
    pro, client = appointment.pro, appointment.client
    if client is not None:
        ClientRecord.objects.get_or_create(
            pro=pro, client=client, defaults={"name": appointment.client_name}
        )
    elif appointment.client_phone:
        ClientRecord.objects.get_or_create(
            pro=pro,
            client=None,
            phone=appointment.client_phone,
            defaults={"name": appointment.client_name},
        )


def _start_deposit(appointment: Appointment, buyer) -> Payment:
    payment = payment_services.create_payment(
        buyer,
        appointment.pro.user,
        purpose=Purpose.DEPOSIT,
        items_minor=appointment.deposit_minor,
        currency=appointment.currency,
        description=f"{appointment.service.name} — {appointment.pro.display_name}"[:200],
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=SOURCE,
        source_id=appointment.pk,
        service_at=appointment.starts_at,
    )
    appointment.payment = payment
    appointment.save(update_fields=["payment", "updated_at"])
    return payment


def _after_hours(pro) -> datetime.datetime:
    hours = int(common.setting("booking.pro_answer_hours", pro, 24))
    return timezone.now() + datetime.timedelta(hours=hours)


@transaction.atomic
def book(
    pro: ProProfile,
    service_id,
    start: datetime.datetime,
    *,
    user=None,
    guest_name: str = "",
    guest_phone: str = "",
    staff_id=None,
    option_ids=(),
    note: str = "",
    source: str = Appointment.Source.ONLINE,
    by_pro=None,
    post=None,
    status: str | None = None,
    gift_card_code: str = "",
    prepaid_minor: int | None = None,
    prepay=None,
) -> Appointment:
    """Books a service: checks again the exact time under a lock (no double booking).

    `by_pro`: the pro (or her collaborator) books for a client on the phone: no notice,
    no deposit, confirmed at once. `status`: forced (the waiting list keeps a place).
    `prepay(appointment) -> Payment`: an offered service (gifts, ADR-014), paid in full at
    `prepaid_minor` (the price paid by the giver), even by a guest.
    """
    booking_settings = BookingSettings.objects.select_for_update().get_or_create(pro=pro)[0]
    pro._booking_settings = booking_settings
    if by_pro is None and not pro.is_published:
        raise errors.ProNotFound()
    service = _service(pro, service_id)
    _staff(pro, staff_id, service)
    options = list(ServiceOption.objects.filter(service=service, pk__in=list(option_ids)))

    phone = ""
    guest = None
    if user is None:
        if by_pro is None and prepay is None and not booking_settings.accepts_guests:
            raise errors.GuestsNotAccepted()
        phone = common.normalize_phone(guest_phone)
        name = (guest_name or "").strip()[:150]
        if not phone or not name:
            raise errors.GuestDetailsNeeded()
        guest = common.guest_for(name, phone)
        client_name = name
    else:
        if user.pk == pro.user_id and by_pro is None:
            raise errors.CannotBookYourself()
        phone = str(user.phone or "")
        client_name = user.first_name or phone

    if by_pro is None:
        _check_time(pro, start)
    slot = availability.find(pro, service, start, staff_id=staff_id, option_ids=option_ids)
    if slot is None:
        raise errors.SlotTaken()

    discount = 0 if by_pro is not None else availability._discount(pro, start, timezone.now())
    price = price_of(service, options, discount)
    deposit = 0
    if prepay is not None:
        discount, price, deposit = 0, prepaid_minor, prepaid_minor
    elif by_pro is None:
        forced = forced_deposit_percent(pro, user=user, phone=phone)
        deposit = deposit_of(service, price, forced_percent=forced)
        if deposit and not gift_card_code and (user is None or not can_purchase(user)):
            raise errors.DepositNeedsAccount()
    covered = bool(deposit and (gift_card_code or prepay is not None))

    if status is None:
        if by_pro is not None:
            status = A.CONFIRMED
        elif deposit and not covered:
            status = A.AWAITING_DEPOSIT
        elif booking_settings.auto_confirm:
            status = A.CONFIRMED
        else:
            status = A.PENDING
    appointment = Appointment.objects.create(
        reference=common.new_reference(),
        pro=pro,
        service=service,
        client=user,
        guest=guest,
        client_name=client_name,
        client_phone=phone,
        starts_at=slot.start,
        ends_at=slot.end,
        status=status,
        source=source,
        price_minor=price,
        currency=service.currency,
        discount_percent=discount,
        deposit_minor=deposit,
        note=(note or "").strip()[:500],
        post=post,
        answer_due_at=_after_hours(pro) if status == A.PENDING else None,
        confirmed_at=timezone.now() if status == A.CONFIRMED else None,
    )
    appointment.options.set(options)
    try:
        with transaction.atomic():
            common.write_steps(appointment, slot)
    except IntegrityError as exc:
        raise errors.SlotTaken() from exc
    if prepay is not None:
        appointment.payment = prepay(appointment)
        appointment.save(update_fields=["payment", "updated_at"])
    elif covered and not common.cover_deposit(appointment, gift_card_code, user):
        raise errors.GiftCardRefused()
    if status == A.AWAITING_DEPOSIT:
        _start_deposit(appointment, user)
    _record_client(appointment)
    common.changed(pro)
    record("booking.booked", appointment, actor=user or by_pro)
    if status == A.CONFIRMED:
        common.tell_client(appointment, "booking.confirmed")
        if by_pro is None:
            common.tell_pro(appointment, "booking.new")
    elif status == A.PENDING:
        common.tell_client(appointment, "booking.requested")
        common.tell_pro(appointment, "booking.request")
    return appointment


def start_deposit_payment(appointment: Appointment, buyer) -> Appointment:
    """The deposit's payment page (created at booking, reopened here)."""
    if appointment.status != A.AWAITING_DEPOSIT or appointment.payment_id is None:
        raise errors.InvalidStep()
    payment_services.start_checkout(appointment.payment, buyer=buyer)
    appointment.payment.refresh_from_db()
    return appointment


# --- The pro's answer ----------------------------------------------------------------------------


def _locked(appointment: Appointment) -> Appointment:
    return (
        Appointment.objects.select_for_update(of=("self",))
        .select_related("pro", "service", "client", "payment")
        .get(pk=appointment.pk)
    )


@transaction.atomic
def confirm(appointment: Appointment, *, actor) -> Appointment:
    appointment = _locked(appointment)
    if appointment.status != A.PENDING:
        raise errors.InvalidStep()
    appointment.status = A.CONFIRMED
    appointment.confirmed_at = timezone.now()
    appointment.answer_due_at = None
    appointment.save(update_fields=["status", "confirmed_at", "answer_due_at", "updated_at"])
    record("booking.confirmed", appointment, actor=actor)
    common.changed(appointment.pro)
    common.tell_client(appointment, "booking.confirmed")
    return appointment


def _give_back_deposit(appointment: Appointment, reason: str) -> None:
    payment = appointment.payment
    if payment is None:
        return
    payment = Payment.objects.get(pk=payment.pk)
    if payment.status == PS.HELD:
        payment_services.refund_full(payment, reason=reason)
    elif payment.status == PS.PENDING_PAYMENT:
        payment_services.mark_not_paid(payment, reason=reason)


def _keep_deposit(appointment: Appointment, reason: str) -> None:
    payment = appointment.payment
    if payment is not None and Payment.objects.get(pk=payment.pk).status == PS.HELD:
        payment_services.release(payment, reason=reason)


def _close(appointment: Appointment, status: str, *, by: str = "", actor=None) -> None:
    appointment.status = status
    fields = ["status", "updated_at"]
    if status in (A.CANCELLED, A.DECLINED, A.EXPIRED):
        appointment.cancelled_at = timezone.now()
        appointment.cancelled_by = by
        fields += ["cancelled_at", "cancelled_by"]
    appointment.save(update_fields=fields)
    common.set_blocking(appointment)
    common.changed(appointment.pro)
    record(f"booking.{status}", appointment, actor=actor)


@transaction.atomic
def decline(appointment: Appointment, *, actor, message: str = "") -> Appointment:
    appointment = _locked(appointment)
    if appointment.status not in (A.PENDING, A.PROPOSED):
        raise errors.InvalidStep()
    appointment.pro_message = (message or "").strip()[:500]
    appointment.save(update_fields=["pro_message", "updated_at"])
    _close(appointment, A.DECLINED, by=Appointment.CancelledBy.PRO, actor=actor)
    _give_back_deposit(appointment, "booking_declined")
    common.tell_client(appointment, "booking.declined", {"message": appointment.pro_message})
    _freed(appointment)
    return appointment


@transaction.atomic
def propose(appointment: Appointment, *, actor, start: datetime.datetime, message: str = ""):
    """Another time, with a message: the client accepts or not (the place is kept)."""
    appointment = _locked(appointment)
    if appointment.status not in (A.PENDING, A.CONFIRMED):
        raise errors.InvalidStep()
    slot = availability.find(
        appointment.pro,
        appointment.service,
        start,
        option_ids=[o.pk for o in appointment.options.all()],
        ignore_appointment=appointment.pk,
    )
    if slot is None:
        raise errors.SlotTaken()
    appointment.proposed_from = appointment.proposed_from or appointment.starts_at
    appointment.starts_at, appointment.ends_at = slot.start, slot.end
    appointment.status = A.PROPOSED
    appointment.pro_message = (message or "").strip()[:500]
    appointment.answer_due_at = _after_hours(appointment.pro)
    appointment.save()
    try:
        with transaction.atomic():
            common.write_steps(appointment, slot)
    except IntegrityError as exc:
        raise errors.SlotTaken() from exc
    common.changed(appointment.pro)
    record("booking.proposed", appointment, actor=actor)
    common.tell_client(appointment, "booking.proposed", {"message": appointment.pro_message})
    return appointment


@transaction.atomic
def answer_proposal(appointment: Appointment, *, accept: bool, actor=None) -> Appointment:
    appointment = _locked(appointment)
    if appointment.status != A.PROPOSED:
        raise errors.InvalidStep()
    if not accept:
        _close(appointment, A.CANCELLED, by=Appointment.CancelledBy.CLIENT, actor=actor)
        _give_back_deposit(appointment, "proposal_refused")
        common.tell_pro(appointment, "booking.proposal_refused")
        _freed(appointment)
        return appointment
    appointment.status = A.CONFIRMED
    appointment.confirmed_at = timezone.now()
    appointment.answer_due_at = None
    appointment.save(update_fields=["status", "confirmed_at", "answer_due_at", "updated_at"])
    common.changed(appointment.pro)
    record("booking.proposal_accepted", appointment, actor=actor)
    common.tell_pro(appointment, "booking.proposal_accepted")
    return appointment


# --- Cancel, move, done, no-show -----------------------------------------------------------------


def free_cancellation_until(appointment: Appointment) -> datetime.datetime:
    own = common.settings_of(appointment.pro).free_cancel_hours
    hours = int(common.setting("booking.free_cancel_hours", appointment.pro, 24, own))
    return appointment.starts_at - datetime.timedelta(hours=hours)


@transaction.atomic
def cancel(appointment: Appointment, *, by: str, actor=None) -> Appointment:
    """By the client: free until the limit, then the pro keeps the deposit. By the pro (or
    automatically): always refunded."""
    appointment = _locked(appointment)
    if appointment.status not in Appointment.BLOCKING:
        raise errors.InvalidStep()
    late = by == Appointment.CancelledBy.CLIENT and timezone.now() > free_cancellation_until(
        appointment
    )
    _close(appointment, A.CANCELLED, by=by, actor=actor)
    if late:
        _keep_deposit(appointment, "late_cancellation")
    else:
        _give_back_deposit(appointment, f"cancelled_by_{by}")
    if by == Appointment.CancelledBy.CLIENT:
        common.tell_pro(appointment, "booking.cancelled_by_client")
        common.tell_client(appointment, "booking.cancelled", {"late": late})
    else:
        common.tell_client(appointment, "booking.cancelled_by_pro")
    _freed(appointment)
    return appointment


@transaction.atomic
def move(appointment: Appointment, *, actor, start: datetime.datetime, staff_id=None):
    """The pro moves an appointment (drag and drop): checked by the engine first."""
    appointment = _locked(appointment)
    if appointment.status not in (A.CONFIRMED, A.PENDING, A.AWAITING_DEPOSIT):
        raise errors.InvalidStep()
    old = appointment.starts_at
    slot = availability.find(
        appointment.pro,
        appointment.service,
        start,
        staff_id=staff_id,
        option_ids=[o.pk for o in appointment.options.all()],
        ignore_appointment=appointment.pk,
    )
    if slot is None:
        raise errors.SlotTaken()
    appointment.starts_at, appointment.ends_at = slot.start, slot.end
    appointment.save(update_fields=["starts_at", "ends_at", "updated_at"])
    try:
        with transaction.atomic():
            common.write_steps(appointment, slot)
    except IntegrityError as exc:
        raise errors.SlotTaken() from exc
    if appointment.payment_id:
        Payment.objects.filter(pk=appointment.payment_id).update(service_at=slot.start)
    common.changed(appointment.pro)
    record("booking.moved", appointment, actor=actor, metadata={"from": old.isoformat()})
    if old != slot.start:
        common.tell_client(appointment, "booking.moved")
        _freed(appointment, day=old)
    return appointment


@transaction.atomic
def complete(appointment: Appointment, *, actor) -> Appointment:
    """Done: the deposit goes to the pro, the client can review."""
    appointment = _locked(appointment)
    if appointment.status != A.CONFIRMED:
        raise errors.InvalidStep()
    if appointment.starts_at > timezone.now():
        raise errors.NotYet()
    appointment.completed_at = timezone.now()
    appointment.save(update_fields=["completed_at", "updated_at"])
    _close(appointment, A.COMPLETED, actor=actor)
    _keep_deposit(appointment, "completed")
    common.run_completed(appointment)
    common.tell_client(appointment, "booking.completed")
    return appointment


def late_tolerance(appointment: Appointment) -> int:
    own = common.settings_of(appointment.pro).late_tolerance_minutes
    return int(common.setting("booking.late_tolerance_minutes", appointment.pro, 15, own))


@transaction.atomic
def no_show(appointment: Appointment, *, actor) -> Appointment:
    """The client did not come: the pro keeps the deposit, the client's rating goes down."""
    appointment = _locked(appointment)
    if appointment.status != A.CONFIRMED:
        raise errors.InvalidStep()
    minutes = late_tolerance(appointment)
    if timezone.now() < appointment.starts_at + datetime.timedelta(minutes=minutes):
        raise errors.NotLateEnough(details={"minutes": minutes})
    _close(appointment, A.NO_SHOW, actor=actor)
    _keep_deposit(appointment, "no_show")
    if appointment.client_id:
        from apps.social.models import ClientRating

        ClientRating.objects.update_or_create(
            source_type="booking",
            source_id=appointment.pk,
            defaults={
                "pro": appointment.pro,
                "client": appointment.client,
                "rating": 1,
                "no_show": True,
            },
        )
    common.tell_client(appointment, "booking.no_show")
    return appointment


def _freed(appointment: Appointment, day=None) -> None:
    from . import waitlist

    moment = day or appointment.starts_at
    pro = appointment.pro
    local_day = moment.astimezone(zone_of(pro)).date()
    transaction.on_commit(lambda: waitlist.offer_freed_place(pro, local_day))


# --- Guests: their link --------------------------------------------------------------------------


def by_token(token: str) -> Appointment:
    found = (
        Appointment.objects.select_related("pro", "service", "payment")
        .prefetch_related("steps__staff")
        .filter(manage_token=token)
        .first()
    )
    if found is None:
        raise errors.AppointmentNotFound()
    return found


# --- The deposit's payment -----------------------------------------------------------------------


def may_cancel_payment(payment: Payment, actor) -> bool:
    """The deposit is never cancelled from the payment page: cancel the appointment."""
    return False


def on_payment_change(payment: Payment) -> None:
    with transaction.atomic():
        appointment = (
            Appointment.objects.select_for_update(of=("self",))
            .select_related("pro", "service", "client")
            .filter(payment_id=payment.pk)
            .first()
        )
        if appointment is None or appointment.status != A.AWAITING_DEPOSIT:
            return
        if payment.status == PS.HELD:
            settings = common.settings_of(appointment.pro)
            if settings.auto_confirm or appointment.group_id or appointment.source == "waitlist":
                appointment.status = A.CONFIRMED
                appointment.confirmed_at = timezone.now()
            else:
                appointment.status = A.PENDING
                appointment.answer_due_at = _after_hours(appointment.pro)
            appointment.save()
            common.changed(appointment.pro)
            if appointment.status == A.CONFIRMED:
                common.tell_client(appointment, "booking.confirmed")
                common.tell_pro(appointment, "booking.new")
            else:
                common.tell_client(appointment, "booking.requested")
                common.tell_pro(appointment, "booking.request")
            if appointment.group_id:
                from .groups import check_group

                transaction.on_commit(lambda: check_group(appointment.group))
        elif payment.status == PS.CANCELLED:
            _close(appointment, A.EXPIRED, by=Appointment.CancelledBy.SYSTEM)
