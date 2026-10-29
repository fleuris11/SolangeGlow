"""Waiting list, group bookings, the pro's set-up, last minute, product advice, iCal."""

import datetime

import pytest
from django.utils import timezone

from apps.booking import errors, selectors
from apps.booking.models import (
    Appointment,
    GroupBooking,
    LastMinuteAlert,
    WaitlistEntry,
)
from apps.booking.services import agenda, appointments, automation, groups, waitlist
from apps.core.choices import Role
from apps.messaging.tests.factories import adult
from apps.notifications.models import ContactMessage, Notification
from apps.payments import services as payments
from apps.payments.models import Payment
from apps.pros.models import ProProfile
from apps.shop.tests.factories import product
from apps.social.models import Follow

from .factories import MONDAY, at, person, salon, service

pytestmark = pytest.mark.django_db
A = Appointment.Status
W = WaitlistEntry.Status
GUEST_PHONE = "+2290197000001"


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = at(8, day=MONDAY - datetime.timedelta(days=2))

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def pay(payment_id):
    payment = Payment.objects.get(pk=payment_id)
    payments.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=str(payment.pk)
    )


def full_day(pro, svc):
    """Every place of the Monday taken (9:00-18:00 by hours)."""
    return [
        appointments.book(pro, svc.pk, at(hour), user=adult(f"Cliente {hour}"))
        for hour in range(9, 18)
    ]


# --- Waiting list ---------------------------------------------------------------------------------


def test_a_freed_place_goes_to_the_first_waiting_client(clock):
    pro = salon()
    svc = service(pro, ("work", 60))
    taken = full_day(pro, svc)
    first = waitlist.join(pro, svc.pk, MONDAY, guest_name="Inès", guest_phone=GUEST_PHONE)
    # The order of the list is the time of joining: the second one comes a minute later.
    clock.set(timezone.now() + datetime.timedelta(minutes=1))
    second = waitlist.join(pro, svc.pk, MONDAY, user=adult("Awa"))
    with pytest.raises(errors.AlreadyInList):
        waitlist.join(pro, svc.pk, MONDAY, user=second.client)
    appointments.cancel(taken[3], by=Appointment.CancelledBy.CLIENT)  # 12:00 frees up
    first.refresh_from_db()
    assert first.status == W.OFFERED and first.offer.status == A.HELD
    assert first.offer.starts_at == at(12)
    assert first.offer_expires_at == timezone.now() + datetime.timedelta(minutes=30)
    assert ContactMessage.objects.filter(event_key="booking.waitlist_offer").exists()
    second.refresh_from_db()
    assert second.status == W.WAITING  # one offer at a time
    held = waitlist.accept(first)
    assert held.status == A.CONFIRMED


def test_an_offer_without_answer_goes_to_the_next(clock):
    pro = salon()
    svc = service(pro, ("work", 60))
    taken = full_day(pro, svc)
    first = waitlist.join(pro, svc.pk, MONDAY, user=adult("Awa"))
    clock.set(timezone.now() + datetime.timedelta(minutes=1))
    second = waitlist.join(pro, svc.pk, MONDAY, user=adult("Inès"))
    appointments.cancel(taken[0], by=Appointment.CancelledBy.PRO)
    first.refresh_from_db()
    clock.set(timezone.now() + datetime.timedelta(minutes=31))
    with pytest.raises(errors.OfferExpired):
        waitlist.accept(first)
    assert waitlist.expire_offers() == 1
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == W.EXPIRED and first.offer.status == A.EXPIRED
    assert second.status == W.OFFERED and second.offer.starts_at == at(9)
    assert "booking.waitlist_offer" in Notification.objects.filter(user=second.client).values_list(
        "event_key", flat=True
    )


def test_the_waiting_hours_are_respected(clock):
    pro = salon()
    svc = service(pro, ("work", 60))
    taken = full_day(pro, svc)
    entry = waitlist.join(
        pro,
        svc.pk,
        MONDAY,
        user=adult("Awa"),
        from_time=datetime.time(15),
        to_time=datetime.time(17),
    )
    appointments.cancel(taken[0], by=Appointment.CancelledBy.CLIENT)  # 9:00: too early
    entry.refresh_from_db()
    assert entry.status == W.WAITING
    appointments.cancel(taken[7], by=Appointment.CancelledBy.CLIENT)  # 16:00
    entry.refresh_from_db()
    assert entry.status == W.OFFERED and entry.offer.starts_at == at(16)
    with pytest.raises(errors.InvalidHours):
        waitlist.join(
            pro,
            svc.pk,
            MONDAY,
            user=adult("Inès"),
            from_time=datetime.time(17),
            to_time=datetime.time(15),
        )


def test_leaving_the_list_frees_the_held_place(clock):
    pro = salon()
    svc = service(pro, ("work", 60))
    taken = full_day(pro, svc)
    entry = waitlist.join(pro, svc.pk, MONDAY, user=adult("Awa"))
    appointments.cancel(taken[0], by=Appointment.CancelledBy.CLIENT)
    entry.refresh_from_db()
    waitlist.leave(entry)
    entry.refresh_from_db()
    assert entry.status == W.CANCELLED and entry.offer.status == A.EXPIRED


def test_a_held_place_with_deposit_waits_for_the_payment(clock):
    pro = salon()
    svc = service(pro, ("work", 60), deposit_kind="amount", deposit_value=5_000)
    taken = [
        appointments.book(pro, svc.pk, at(hour), user=adult(f"Cliente {hour}"))
        for hour in range(9, 18)
    ]
    for appointment in taken:
        pay(appointment.payment_id)
    entry = waitlist.join(pro, svc.pk, MONDAY, user=adult("Awa"))
    appointments.cancel(taken[2], by=Appointment.CancelledBy.CLIENT)
    entry.refresh_from_db()
    held = waitlist.accept(entry)
    assert held.status == A.AWAITING_DEPOSIT and held.payment_id
    pay(held.payment_id)
    held.refresh_from_db()
    assert held.status == A.CONFIRMED


# --- Groups ---------------------------------------------------------------------------------------


def test_a_group_without_deposit_is_confirmed():
    pro = salon()
    person(pro, "Carine")
    svc = service(pro, ("work", 60))
    bride = adult("Mireille")
    group = groups.create_group(bride, pro, svc.pk, at(9), 3, title="Mariage")
    rows = list(group.appointments.order_by("starts_at", "created_at"))
    assert group.status == GroupBooking.Status.CONFIRMED and len(rows) == 3
    assert [r.starts_at for r in rows] == [at(9), at(10), at(11)]  # two people, three clients
    assert rows[0].client == bride and rows[1].client is None
    assert "booking.group" in Notification.objects.filter(user=pro.user).values_list(
        "event_key", flat=True
    )


def test_group_limits():
    pro = salon()
    svc = service(pro, ("work", 60))
    with pytest.raises(errors.InvalidGroup) as size:
        groups.create_group(adult(), pro, svc.pk, at(9), 9)
    assert size.value.details == {"max": 8}
    with pytest.raises(errors.GroupDoesNotFit):
        groups.create_group(adult(), pro, svc.pk, at(16), 3)
    with pytest.raises(errors.CannotBookYourself):
        groups.create_group(pro.user, pro, svc.pk, at(9), 2)


def test_each_member_pays_her_share_then_the_rest_is_released(clock):
    pro = salon()
    person(pro, "Carine")
    person(pro, "Fifamè")
    svc = service(pro, ("work", 60), deposit_kind="percent", deposit_value=50)
    bride = adult("Mireille")
    group = groups.create_group(bride, pro, svc.pk, at(9), 3)
    assert group.status == GroupBooking.Status.COLLECTING
    mine = groups.claim_share(group, bride)
    friend = adult("Sika")
    hers = groups.claim_share(group, friend)
    assert mine.client == bride and hers.client == friend and hers.pk != mine.pk
    pay(mine.payment_id)
    pay(hers.payment_id)
    group.refresh_from_db()
    assert group.status == GroupBooking.Status.COLLECTING  # one share left
    clock.set(timezone.now() + datetime.timedelta(hours=25))
    assert groups.close_unpaid() == 1
    group.refresh_from_db()
    assert group.status == GroupBooking.Status.CONFIRMED
    statuses = sorted(group.appointments.values_list("status", flat=True))
    assert statuses == [A.CONFIRMED, A.CONFIRMED, A.EXPIRED]


def test_the_organiser_can_pay_every_share():
    pro = salon()
    person(pro, "Carine")
    svc = service(pro, ("work", 60), deposit_kind="amount", deposit_value=4_000)
    bride = adult("Mireille")
    group = groups.create_group(bride, pro, svc.pk, at(9), 2)
    for _ in range(2):
        pay(groups.claim_share(group, bride).payment_id)
    assert groups.check_group(group).status == GroupBooking.Status.CONFIRMED
    with pytest.raises(errors.InvalidStep):
        groups.claim_share(group, bride)


# --- The agenda's set-up --------------------------------------------------------------------------


def test_a_collaborator_with_an_account_is_linked():
    pro = salon()
    carine = adult("Carine", phone="+2290197000009")
    staff = agenda.save_staff(pro, name="Carine", color="#7A3E9D", phone="01 97 00 00 09")
    assert staff.user == carine
    carine.refresh_from_db()
    assert Role.COLLABORATOR in carine.roles
    assert selectors.agenda_access(carine, pro.pk) == (pro, {staff.pk})
    assert selectors.agenda_access(pro.user, pro.pk)[1] is None  # the pro sees everyone
    with pytest.raises(errors.InvalidStaff):
        agenda.save_staff(pro, name="Carine", color="red")


def test_a_collaborator_who_signs_up_later_is_linked():
    pro = salon()
    staff = agenda.save_staff(pro, name="Sika", phone="+2290197000010")
    assert staff.user is None
    later = adult("Sika", phone="+2290197000010")
    assert [m.pk for m in selectors.memberships(later)] == [staff.pk]


def test_own_hours_and_breaks_replace_the_old_ones():
    pro = salon()
    staff = agenda.save_staff(pro, name="Sika", own_hours=True)
    nine, five = datetime.time(9), datetime.time(17)
    agenda.set_hours(pro, staff.pk, [{"weekday": 0, "starts_at": nine, "ends_at": five}])
    agenda.set_hours(pro, staff.pk, [{"weekday": 1, "starts_at": nine, "ends_at": five}])
    assert list(staff.periods.values_list("weekday", flat=True)) == [1]
    with pytest.raises(errors.InvalidHours):
        agenda.set_hours(pro, staff.pk, [{"weekday": 1, "starts_at": five, "ends_at": nine}])


def test_block_a_range_and_remove_it():
    pro = salon()
    svc = service(pro, ("work", 60))
    off = agenda.add_time_off(pro, starts_at=at(9), ends_at=at(18), kind="block", note="Salon")
    with pytest.raises(errors.SlotTaken):
        appointments.book(pro, svc.pk, at(10), user=adult())
    agenda.remove_time_off(pro, off.pk)
    assert appointments.book(pro, svc.pk, at(10), user=adult()).status == A.CONFIRMED


def test_client_record_and_history():
    pro = salon()
    svc = service(pro, ("work", 60))
    client = adult("Awa")
    first = appointments.book(pro, svc.pk, at(10), user=client)
    appointments.book(pro, svc.pk, at(10, day=MONDAY + datetime.timedelta(days=7)), user=client)
    found = agenda.record_for(pro, first)
    agenda.update_record(pro, found.pk, notes="Cuir chevelu sensible", preferences="Thé")
    found.refresh_from_db()
    assert found.notes == "Cuir chevelu sensible"
    assert len(agenda.history_of(found)) == 2


def test_product_advice_after_the_appointment(clock):
    pro = salon(verification_status=ProProfile.Verification.VERIFIED)
    oil = product(pro.user, title="Huile de ricin")
    client = adult("Awa")
    booked = appointments.book(pro, service(pro, ("work", 60)).pk, at(10), user=client)
    with pytest.raises(errors.InvalidStep):
        agenda.recommend(pro, booked, oil.pk)
    clock.set(at(11))
    appointments.complete(booked, actor=pro.user)
    booked.refresh_from_db()
    advice = agenda.recommend(pro, booked, oil.pk, note="Deux fois par semaine")
    assert advice.product == oil
    assert agenda.recommend(pro, booked, oil.pk) == advice  # once
    assert Notification.objects.filter(user=client, event_key="booking.advice").count() == 1
    with pytest.raises(errors.ProductNotFound):
        agenda.recommend(pro, booked, product(title="Ailleurs").pk)


def test_last_minute_discount_and_alerts(clock):
    pro = salon(city="Cotonou")
    svc = service(pro, ("work", 60))
    near = adult("Awa", city="Cotonou")
    far = adult("Inès", city="Parakou")
    Follow.objects.create(follower=near, followed=pro.user)
    Follow.objects.create(follower=far, followed=pro.user)
    clock.set(at(8))
    agenda.set_last_minute(pro, percent_off=20, window_hours=6, is_active=True)
    assert set(LastMinuteAlert.objects.values_list("user__first_name", flat=True)) == {"Awa"}
    assert agenda.announce_last_minute(pro.last_minute) == 0  # once a day
    soon = appointments.book(pro, svc.pk, at(10), user=adult("Sika"))
    later = appointments.book(pro, svc.pk, at(16), user=adult("Yasmine"))
    assert (soon.discount_percent, soon.price_minor) == (20, 16_000)
    assert (later.discount_percent, later.price_minor) == (0, 20_000)


def test_ical_export():
    pro = salon()
    svc = service(pro, ("work", 60), name="Tresses, nattes")
    appointments.book(
        pro,
        svc.pk,
        at(10, day=timezone.localdate() + datetime.timedelta(days=3)),
        user=adult("Awa"),
    )
    text = agenda.ical(pro)
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:Tresses\\, nattes - Awa" in text


def test_reminders_and_deadlines_run_together(clock):
    pro = salon()
    appointments.book(pro, service(pro, ("work", 60)).pk, at(10), user=adult())
    clock.set(at(9))
    assert automation.run_all() == {"reminders": 1, "answers": 0, "waitlist": 0, "groups": 0}


def test_a_service_keeps_its_deposit_and_its_equipment():
    from apps.pros import errors as pro_errors
    from apps.pros.services import save_service

    pro = salon()
    basin = agenda.save_resource(pro, name="Bac", quantity=1)
    saved = save_service(
        pro,
        {
            "name": "Coloration",
            "price_kind": "fixed",
            "price_minor": 20_000,
            "deposit_kind": "percent",
            "deposit_value": 30,
            "steps": [
                {"kind": "work", "duration_minutes": 30},
                {"kind": "wait", "duration_minutes": 30, "resource_id": basin.pk},
                {"kind": "work", "duration_minutes": 15, "other_staff_ok": True},
            ],
        },
    )
    steps = list(saved.steps.order_by("position"))
    assert steps[1].resource_need.resource == basin and steps[2].other_staff_ok
    assert appointments.deposit_of(saved, 20_000) == 6_000
    with pytest.raises(pro_errors.InvalidDeposit):
        save_service(pro, {"deposit_kind": "percent", "deposit_value": 150}, service=saved)
