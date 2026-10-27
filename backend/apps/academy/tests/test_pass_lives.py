"""The monthly pass (paid month by month, never taken automatically) and the training lives
(planning, registration, reminders, waiting room)."""

import datetime

import pytest
from django.utils import timezone

from apps.academy import errors, selectors
from apps.academy.models import AcademyPass, Course, LiveSession
from apps.academy.services import enrollments, lives, passes
from apps.academy.services.common import PASS_SOURCE
from apps.invoicing.models import Document
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification
from apps.payments.models import Payment

from .factories import course, pay, setting, trainer

pytestmark = pytest.mark.django_db
PS = Payment.Status


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = timezone.now()

        def move(self, **delta):
            self.value = self.value + datetime.timedelta(**delta)

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def events(user):
    return set(Notification.objects.filter(user=user).values_list("event_key", flat=True))


def test_the_pass_opens_the_courses_of_the_pass_month_by_month(clock):
    student = adult("Awa")
    in_pass = course(None, pricing=Course.Pricing.PASS, country=student.country)
    with pytest.raises(errors.PassNotOffered):  # no price in this country yet
        passes.subscribe(student)
    setting("academy.pass_price_minor", 2000)
    with pytest.raises(errors.PassRequired):
        enrollments.get_course(student, in_pass)

    payment = pay(passes.subscribe(student))
    assert (payment.status, payment.purpose, payment.buyer_fee_minor) == (
        PS.RELEASED,
        "academy_pass",
        0,
    )
    assert selectors.has_pass(student)
    assert Document.objects.filter(source_type=PASS_SOURCE, source_id=payment.pk).exists()
    with pytest.raises(errors.PassActive):
        passes.subscribe(student)
    enrollment, url = enrollments.get_course(student, in_pass)
    assert url is None and enrollment.access == "pass"
    assert selectors.can_watch(student, in_pass)

    # A few days before the end: the payment of next month, then the pass stops if unpaid.
    clock.move(days=28)
    assert passes.send_renewals() == 1
    assert "academy.pass_renewal_due" in events(student)
    clock.move(days=5)
    assert passes.end_periods() == 1
    assert not selectors.has_pass(student)
    assert not selectors.can_watch(student, in_pass)
    assert "academy.pass_ended" in events(student)

    # Paid again: a new month from today, the courses open again.
    academy_pass = AcademyPass.objects.get(user=student)
    pay(academy_pass.renewal_payment)
    assert selectors.has_pass(student) and selectors.can_watch(student, in_pass)


def test_stopping_the_pass_cancels_the_waiting_payment():
    student = adult("Awa")
    setting("academy.pass_price_minor", 2000)
    pay(passes.subscribe(student))
    academy_pass = AcademyPass.objects.get(user=student)
    academy_pass.current_period_end = timezone.now() + datetime.timedelta(days=1)
    academy_pass.save()
    passes.send_renewals()
    waiting = AcademyPass.objects.get(user=student).renewal_payment
    stopped = passes.cancel(student)
    assert stopped.cancel_at_period_end and stopped.renewal_payment is None
    assert Payment.objects.get(pk=waiting.pk).status == PS.CANCELLED
    assert passes.send_renewals() == 0


def plan(pro, **values):
    values.setdefault("title", "Maquillage mariée : vos questions")
    values.setdefault("starts_at", timezone.now() + datetime.timedelta(days=2))
    values.setdefault("duration_minutes", 45)
    values.setdefault("capacity", 2)
    return lives.plan_live(pro.user, **values)


def test_a_live_is_planned_its_students_invited_and_places_counted():
    pro = trainer()
    taught = course(pro)
    student = adult("Awa")
    enrollments.get_course(student, taught)
    with pytest.raises(errors.InvalidLive):
        plan(pro, starts_at=timezone.now() - datetime.timedelta(hours=1))
    live = plan(pro, course_id=taught.pk)
    assert "academy.live_invitation" in events(student)

    lives.register(student, live)
    lives.register(student, live)  # twice: one place
    lives.register(adult("Bintou"), live)
    live.refresh_from_db()
    assert live.registered_count == 2
    with pytest.raises(errors.LiveFull):
        lives.register(adult("Céline"), live)
    lives.unregister(student, live)
    live.refresh_from_db()
    assert live.registered_count == 1


def test_reminders_and_the_waiting_room(clock):
    pro = trainer()
    student = adult("Awa")
    live = plan(pro, starts_at=timezone.now() + datetime.timedelta(days=2))
    lives.register(student, live)
    assert lives.send_reminders() == 0
    clock.move(days=1, hours=1)
    assert lives.send_reminders() == 1
    assert lives.send_reminders() == 0  # once
    assert "academy.live_reminder" in events(student)

    state = lives.room(student, live)
    assert state["registered"] and not state["open"] and state["seconds_left"] > 0

    clock.move(hours=22, minutes=50)  # 10 minutes before
    assert lives.send_reminders() == 1
    assert "academy.live_starting" in events(student)
    assert lives.room(student, live)["open"]
    assert not lives.room(adult("Pas inscrite"), live)["open"]

    clock.move(hours=1)
    assert lives.close_lives() == 1
    live.refresh_from_db()
    assert live.status == LiveSession.Status.ENDED


def test_a_cancelled_live_tells_the_registered_students():
    pro = trainer()
    student = adult("Awa")
    live = plan(pro)
    lives.register(student, live)
    with pytest.raises(errors.NotTrainer):
        lives.cancel_live(live, student)
    cancelled = lives.cancel_live(live, pro.user)
    assert cancelled.status == LiveSession.Status.CANCELLED
    assert "academy.live_cancelled" in events(student)
    with pytest.raises(errors.LiveNotFound):
        lives.register(adult("Bintou"), cancelled)
