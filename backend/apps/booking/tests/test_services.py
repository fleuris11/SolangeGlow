"""The life of an appointment: booking, answers, cancellations, deposits, no-shows."""

import datetime

import pytest
from django.utils import timezone

from apps.booking import errors, selectors
from apps.booking.models import Appointment, ClientRecord
from apps.booking.services import agenda, appointments, automation
from apps.messaging.tests.factories import adult
from apps.notifications.models import ContactMessage, Notification
from apps.payments import services as payments
from apps.payments.models import Payment
from apps.social import services as social
from apps.social.models import ClientRating

from .factories import MONDAY, at, salon, service

pytestmark = pytest.mark.django_db
A = Appointment.Status
GUEST_PHONE = "+2290197000001"


@pytest.fixture
def clock(monkeypatch):
    """timezone.now() at a chosen moment."""

    class Clock:
        value = at(8, day=MONDAY - datetime.timedelta(days=2))

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def events(user):
    return list(Notification.objects.filter(user=user).values_list("event_key", flat=True))


def pay(appointment):
    payment = Payment.objects.get(pk=appointment.payment_id)
    payments.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=str(payment.pk)
    )
    appointment.refresh_from_db()
    return appointment


def with_deposit(pro, percent=30):
    return service(pro, ("work", 60), deposit_kind="percent", deposit_value=percent)


# --- Booking --------------------------------------------------------------------------------------


def test_a_client_books_and_it_is_confirmed_by_itself():
    pro = salon()
    svc = service(pro, ("work", 60))
    client = adult("Awa")
    booked = appointments.book(pro, svc.pk, at(10), user=client)
    assert booked.status == A.CONFIRMED and booked.price_minor == 20_000
    assert booked.reference.startswith("RDV-") and booked.steps.count() == 1
    assert "booking.confirmed" in events(client) and "booking.new" in events(pro.user)
    assert ClientRecord.objects.filter(pro=pro, client=client).exists()


def test_a_guest_books_with_her_phone_and_gets_a_whatsapp():
    pro = salon()
    svc = service(pro, ("work", 60))
    booked = appointments.book(pro, svc.pk, at(10), guest_name="Inès", guest_phone="01 97 00 00 01")
    assert booked.client is None and booked.guest is not None
    assert booked.client_phone == GUEST_PHONE and booked.manage_token
    message = ContactMessage.objects.get(event_key="booking.confirmed")
    assert message.channel == "whatsapp" and "/rdv/" in message.body
    assert appointments.by_token(booked.manage_token) == booked


def test_guest_details_and_guests_refused():
    pro = salon()
    svc = service(pro, ("work", 60))
    with pytest.raises(errors.GuestDetailsNeeded):
        appointments.book(pro, svc.pk, at(10), guest_name="Inès", guest_phone="12")
    agenda.update_settings(pro, accepts_guests=False)
    with pytest.raises(errors.GuestsNotAccepted):
        appointments.book(pro, svc.pk, at(10), guest_name="Inès", guest_phone=GUEST_PHONE)


def test_refusals_of_booking():
    pro = salon()
    svc = service(pro, ("work", 60))
    with pytest.raises(errors.CannotBookYourself):
        appointments.book(pro, svc.pk, at(10), user=pro.user)
    with pytest.raises(errors.ServiceNotFound):
        appointments.book(pro, salon("Autre").pk, at(10), user=adult())
    with pytest.raises(errors.SlotTaken):
        appointments.book(pro, svc.pk, at(17, 30), user=adult())  # ends after closing
    agenda.update_settings(pro, horizon_days=10)
    with pytest.raises(errors.TooFar) as far:
        appointments.book(pro, svc.pk, at(10), user=adult())
    assert far.value.details == {"days": 10}


def test_too_soon(clock):
    pro = salon()
    agenda.update_settings(pro, min_notice_minutes=120)
    svc = service(pro, ("work", 60))
    clock.set(at(9))
    with pytest.raises(errors.TooSoon) as soon:
        appointments.book(pro, svc.pk, at(10), user=adult())
    assert soon.value.details == {"minutes": 120}
    assert appointments.book(pro, svc.pk, at(11), user=adult()).status == A.CONFIRMED


def test_the_pro_books_a_phone_client_without_notice(clock):
    pro = salon()
    agenda.update_settings(pro, min_notice_minutes=600)
    svc = with_deposit(pro)
    clock.set(at(9))
    booked = appointments.book(
        pro,
        svc.pk,
        at(9, 30),
        guest_name="Mamie",
        guest_phone=GUEST_PHONE,
        source=Appointment.Source.PHONE,
        by_pro=pro.user,
    )
    assert booked.status == A.CONFIRMED and booked.deposit_minor == 0


# --- The pro's answer -----------------------------------------------------------------------------


def test_manual_confirmation_accept_and_decline():
    pro = salon()
    agenda.update_settings(pro, auto_confirm=False)
    svc = service(pro, ("work", 60))
    client = adult("Awa")
    asked = appointments.book(pro, svc.pk, at(10), user=client)
    assert asked.status == A.PENDING and asked.answer_due_at is not None
    assert "booking.request" in events(pro.user)
    appointments.confirm(asked, actor=pro.user)
    asked.refresh_from_db()
    assert asked.status == A.CONFIRMED and asked.answer_due_at is None
    other = appointments.book(pro, svc.pk, at(14), user=adult("Inès"))
    appointments.decline(other, actor=pro.user, message="Je suis en formation.")
    other.refresh_from_db()
    assert other.status == A.DECLINED and not other.steps.filter(blocking=True).exists()
    with pytest.raises(errors.InvalidStep):
        appointments.confirm(other, actor=pro.user)


def test_another_time_proposed_then_accepted_or_refused():
    pro = salon()
    agenda.update_settings(pro, auto_confirm=False)
    svc = service(pro, ("work", 60))
    client = adult("Awa")
    asked = appointments.book(pro, svc.pk, at(10), user=client)
    appointments.propose(asked, actor=pro.user, start=at(15), message="Plutôt l'après-midi ?")
    asked.refresh_from_db()
    assert asked.status == A.PROPOSED and asked.starts_at == at(15)
    assert asked.proposed_from == at(10) and "booking.proposed" in events(client)
    assert asked.steps.get().starts_at == at(15)
    appointments.answer_proposal(asked, accept=True, actor=client)
    asked.refresh_from_db()
    assert asked.status == A.CONFIRMED
    second = appointments.book(pro, svc.pk, at(10), user=adult("Inès"))
    appointments.propose(second, actor=pro.user, start=at(16))
    appointments.answer_proposal(second, accept=False)
    second.refresh_from_db()
    assert second.status == A.CANCELLED and "booking.proposal_refused" in events(pro.user)


def test_a_proposed_time_must_be_free():
    pro = salon()
    svc = service(pro, ("work", 60))
    appointments.book(pro, svc.pk, at(15), user=adult("Inès"))
    first = appointments.book(pro, svc.pk, at(10), user=adult("Awa"))
    with pytest.raises(errors.SlotTaken):
        appointments.propose(first, actor=pro.user, start=at(15))
    appointments.propose(first, actor=pro.user, start=at(10, 30))  # overlaps itself: fine


def test_requests_without_answer_are_cancelled_and_refunded(clock):
    pro = salon()
    agenda.update_settings(pro, auto_confirm=False)
    svc = with_deposit(pro)
    client = adult("Awa")
    asked = pay(appointments.book(pro, svc.pk, at(10), user=client))
    assert asked.status == A.PENDING
    clock.set(timezone.now() + datetime.timedelta(hours=25))
    assert automation.expire_answers() == 1
    asked.refresh_from_db()
    assert asked.status == A.CANCELLED and asked.cancelled_by == "system"
    assert Payment.objects.get(pk=asked.payment_id).status in ("refunded", "partially_refunded")


# --- Deposits and cancellation --------------------------------------------------------------------


def test_deposit_then_confirmed_when_paid():
    pro = salon()
    svc = with_deposit(pro, 30)
    client = adult("Awa")
    booked = appointments.book(pro, svc.pk, at(10), user=client)
    assert booked.status == A.AWAITING_DEPOSIT and booked.deposit_minor == 6_000
    payment = Payment.objects.get(pk=booked.payment_id)
    assert payment.purpose == "deposit" and payment.service_at == at(10)
    assert appointments.may_cancel_payment(payment, client) is False
    assert pay(booked).status == A.CONFIRMED


def test_a_guest_cannot_pay_a_deposit():
    pro = salon()
    svc = with_deposit(pro)
    with pytest.raises(errors.DepositNeedsAccount):
        appointments.book(pro, svc.pk, at(10), guest_name="Inès", guest_phone=GUEST_PHONE)


def test_an_unpaid_deposit_expires():
    pro = salon()
    booked = appointments.book(pro, with_deposit(pro).pk, at(10), user=adult())
    payments.mark_not_paid(Payment.objects.get(pk=booked.payment_id), reason="test")
    booked.refresh_from_db()
    assert booked.status == A.EXPIRED and not booked.steps.filter(blocking=True).exists()


def test_free_cancellation_refunds_the_deposit(clock):
    pro = salon()
    client = adult("Awa")
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=client))
    clock.set(at(9, day=MONDAY - datetime.timedelta(days=1)))  # 25 h before
    appointments.cancel(booked, by=Appointment.CancelledBy.CLIENT, actor=client)
    assert Payment.objects.get(pk=booked.payment_id).status == "refunded"
    assert "booking.cancelled_by_client" in events(pro.user)


def test_late_cancellation_keeps_the_deposit(clock):
    pro = salon()
    client = adult("Awa")
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=client))
    clock.set(at(8))
    appointments.cancel(booked, by=Appointment.CancelledBy.CLIENT, actor=client)
    assert Payment.objects.get(pk=booked.payment_id).status == "released"


def test_the_pro_cancels_late_and_the_client_is_refunded(clock):
    pro = salon()
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=adult()))
    clock.set(at(9, 55))
    appointments.cancel(booked, by=Appointment.CancelledBy.PRO, actor=pro.user)
    assert Payment.objects.get(pk=booked.payment_id).status == "refunded"


def test_move_keeps_the_payment_in_step():
    pro = salon()
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=adult()))
    appointments.move(booked, actor=pro.user, start=at(14))
    booked.refresh_from_db()
    assert booked.starts_at == at(14) and booked.steps.get().starts_at == at(14)
    assert Payment.objects.get(pk=booked.payment_id).service_at == at(14)


# --- Done and no-show -----------------------------------------------------------------------------


def test_done_gives_the_deposit_and_opens_the_review(clock):
    pro = salon()
    client = adult("Awa")
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=client))
    with pytest.raises(errors.NotYet):
        appointments.complete(booked, actor=pro.user)
    clock.set(at(11, 5))
    appointments.complete(booked, actor=pro.user)
    booked.refresh_from_db()
    assert booked.status == A.COMPLETED
    assert Payment.objects.get(pk=booked.payment_id).status == "released"
    assert [t.id for t in social.pending_reviews(client)] == [booked.pk]
    review = social.create_review(client, kind="booking", transaction_id=booked.pk, rating=5)
    assert review.pro_id == pro.pk


def test_no_review_before_the_end_or_for_someone_else(clock):
    pro = salon()
    client = adult("Awa")
    booked = appointments.book(pro, service(pro, ("work", 60)).pk, at(10), user=client)
    with pytest.raises(Exception):  # noqa: B017 - social's NotFinished
        social.create_review(client, kind="booking", transaction_id=booked.pk, rating=5)
    clock.set(at(11, 5))
    appointments.complete(booked, actor=pro.user)
    with pytest.raises(Exception):  # noqa: B017 - social's NotYourTransaction
        social.create_review(adult("Inès"), kind="booking", transaction_id=booked.pk, rating=1)


def test_no_show_after_the_tolerance(clock):
    pro = salon()
    client = adult("Awa")
    booked = pay(appointments.book(pro, with_deposit(pro).pk, at(10), user=client))
    clock.set(at(10, 10))
    with pytest.raises(errors.NotLateEnough) as early:
        appointments.no_show(booked, actor=pro.user)
    assert early.value.details == {"minutes": 15}
    clock.set(at(10, 16))
    appointments.no_show(booked, actor=pro.user)
    booked.refresh_from_db()
    assert booked.status == A.NO_SHOW
    assert Payment.objects.get(pk=booked.payment_id).status == "released"
    assert ClientRating.objects.get(source_id=booked.pk).no_show is True


def test_two_no_shows_make_a_deposit_compulsory(clock):
    client = adult("Awa", phone=GUEST_PHONE)
    for name in ("Salon Un", "Salon Deux"):
        other = salon(name)
        missed = appointments.book(other, service(other, ("work", 30)).pk, at(9), user=client)
        clock.set(at(9, 30))
        appointments.no_show(missed, actor=other.user)
        clock.set(at(8))
    assert selectors.no_shows(user=client) == 2
    pro = salon()
    svc = service(pro, ("work", 60))  # no deposit of its own
    booked = appointments.book(
        pro, svc.pk, at(10, day=MONDAY + datetime.timedelta(days=1)), user=client
    )
    assert booked.status == A.AWAITING_DEPOSIT and booked.deposit_minor == 6_000
    # A guest with the same number is recognised: she must create an account.
    with pytest.raises(errors.DepositNeedsAccount):
        appointments.book(
            pro,
            svc.pk,
            at(15, day=MONDAY + datetime.timedelta(days=1)),
            guest_name="Awa",
            guest_phone=GUEST_PHONE,
        )


# --- Reminders ------------------------------------------------------------------------------------


def test_reminders_once_each(clock):
    pro = salon()
    booked = appointments.book(
        pro, service(pro, ("work", 60)).pk, at(10), guest_name="Inès", guest_phone=GUEST_PHONE
    )
    clock.set(at(9, day=MONDAY - datetime.timedelta(days=1)))  # 25 h before
    assert automation.send_reminders() == 0
    clock.set(at(11, day=MONDAY - datetime.timedelta(days=1)))
    assert automation.send_reminders() == 1
    assert automation.send_reminders() == 0
    clock.set(at(8, 30))
    assert automation.send_reminders() == 1
    booked.refresh_from_db()
    assert booked.reminders_sent == [2, 24]
    assert ContactMessage.objects.filter(event_key="booking.reminder").count() == 2


def test_reminder_skips_the_far_one_when_late(clock):
    pro = salon()
    booked = appointments.book(pro, service(pro, ("work", 60)).pk, at(10), user=adult())
    clock.set(at(9))
    assert automation.send_reminders() == 1
    booked.refresh_from_db()
    assert booked.reminders_sent == [2, 24]
