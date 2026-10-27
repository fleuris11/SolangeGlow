"""Getting a course (free, bought, pass), the right to change her mind, watching, quizzes,
the certificate and the badge."""

import datetime

import pytest
from django.utils import timezone

from apps.academy import errors, selectors
from apps.academy.models import Certificate, Course, Enrollment
from apps.academy.services import enrollments, progress
from apps.invoicing.models import Document
from apps.messaging.tests.factories import adult, minor
from apps.notifications.models import Notification
from apps.payments.models import Payment

from .factories import course, pay, trainer

pytestmark = pytest.mark.django_db
E = Enrollment.Status
PS = Payment.Status
WAIVER = "Je commence tout de suite et je renonce à mon droit de rétractation."


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = timezone.now()

        def move(self, **delta):
            self.value = self.value + datetime.timedelta(**delta)

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def buy(student, bought: Course) -> Enrollment:
    enrollment, url = enrollments.get_course(
        student, bought, waiver=True, waiver_text=WAIVER, ip="203.0.113.7"
    )
    assert url
    pay(enrollment.payment)
    return Enrollment.objects.select_related("payment").get(pk=enrollment.pk)


def test_a_free_course_opens_at_once_and_only_once():
    student = adult("Awa")
    free = course(trainer())
    enrollment, url = enrollments.get_course(student, free)
    assert url is None and (enrollment.status, enrollment.access) == (E.ACTIVE, "free")
    free.refresh_from_db()
    assert free.students_count == 1
    with pytest.raises(errors.AlreadyEnrolled):
        enrollments.get_course(student, free)
    with pytest.raises(errors.AlreadyEnrolled):  # the trainer does not enrol in her own course
        enrollments.get_course(free.pro.user, free)


def test_a_bought_course_needs_the_waiver_then_the_money_waits_for_the_first_lesson():
    pro = trainer()
    student = adult("Awa")
    paid = course(pro, pricing=Course.Pricing.PAID, price=5000)
    with pytest.raises(errors.WaiverRequired):
        enrollments.get_course(student, paid)
    with pytest.raises(errors.CannotBuy):
        enrollments.get_course(minor(), paid, waiver=True, waiver_text=WAIVER)

    enrollment = buy(student, paid)
    assert enrollment.status == E.ACTIVE and enrollment.waiver_text == WAIVER
    assert enrollment.waiver_ip_hash and "203.0.113.7" not in enrollment.waiver_ip_hash
    payment = enrollment.payment
    assert payment.status == PS.HELD
    assert payment.buyer_fee_minor == 0  # no buyer protection: refund within 14 days instead
    assert payment.commission_minor == 750  # 15 % for the platform
    assert Document.objects.filter(source_type="academy", source_id=payment.pk).exists()
    assert Notification.objects.filter(user=student, event_key="academy.course_ready").exists()
    assert Notification.objects.filter(user=pro.user, event_key="academy.course_sold").exists()

    lesson = paid.modules.first().lessons.last()  # not a preview
    state = progress.playback(student, lesson)
    assert state["urls"]["low"] and state["urls"]["medium"]
    enrollment.refresh_from_db()
    assert enrollment.started_at is not None
    assert Payment.objects.get(pk=payment.pk).status == PS.RELEASED
    with pytest.raises(errors.RefundClosed):
        enrollments.refund(enrollment, student)


def test_refund_within_fourteen_days_before_opening_a_lesson(clock):
    student = adult("Awa")
    paid = course(trainer(), pricing=Course.Pricing.PAID, price=5000)
    enrollment = buy(student, paid)
    back = enrollments.refund(enrollment, student)
    assert back.status == E.REFUNDED
    assert Payment.objects.get(pk=enrollment.payment_id).status == PS.REFUNDED
    paid.refresh_from_db()
    assert paid.students_count == 0
    assert not selectors.can_watch(student, paid)

    # Bought again, never opened: after the 14 days the trainer is paid anyway.
    again = buy(student, paid)
    clock.move(days=15)
    with pytest.raises(errors.RefundClosed):
        enrollments.refund(again, student)
    assert enrollments.release_unstarted() == 1
    assert Payment.objects.get(pk=again.payment_id).status == PS.RELEASED


def test_lessons_are_locked_except_the_free_preview():
    paid = course(trainer(), pricing=Course.Pricing.PAID, price=5000)
    lessons = list(paid.modules.first().lessons.all())
    visitor = adult("Curieuse")
    assert progress.playback(visitor, lessons[0])["urls"]["low"]  # preview
    with pytest.raises(errors.NotEnrolled):
        progress.playback(visitor, lessons[1])
    with pytest.raises(errors.NotEnrolled):
        progress.save_position(visitor, lessons[1], seconds=10)


def test_resume_progress_quiz_certificate_and_badge():
    pro_student = trainer("Bintou")  # a pro who follows a course of the platform
    student = pro_student.user
    badge_course = course(
        None, modules=(("Hygiène", 2),), quiz=2, badge=True, country=pro_student.country
    )
    enrollments.get_course(student, badge_course)
    module = badge_course.modules.first()
    first, second = list(module.lessons.all())

    progress.playback(student, first)
    enrollment = progress.save_position(student, first, seconds=100)
    assert progress.playback(student, first)["position_seconds"] == 100  # resume
    assert enrollment.progress_percent == 0

    with pytest.raises(errors.QuizLocked):
        progress.submit_quiz(student, module, [0, 0])
    progress.save_position(student, first, seconds=230)  # 90 % of 240 s
    progress.save_position(student, second, seconds=12, ended=True)
    with pytest.raises(errors.InvalidAnswers):
        progress.submit_quiz(student, module, [0])

    failed = progress.submit_quiz(student, module, [1, 0])
    assert (failed["score_percent"], failed["passed"]) == (50, False)
    assert [line["right"] for line in failed["results"]] == [False, True]
    assert failed["enrollment"].progress_percent == 67  # 2 lessons + 1 quiz: 2 of 3 steps

    passed = progress.submit_quiz(student, module, [0, 0])
    assert passed["passed"] and passed["enrollment"].progress_percent == 100
    certificate = Certificate.objects.get(enrollment__user=student)
    assert certificate.course_title == badge_course.title
    assert certificate.trainer_name == "Solange Glow"
    assert progress.certificate_by_code(certificate.code.lower()).pk == certificate.pk
    pro_student.refresh_from_db()
    assert pro_student.is_trained
    events = set(Notification.objects.filter(user=student).values_list("event_key", flat=True))
    assert {"academy.certificate_ready", "academy.badge_earned"} <= events

    revoked = progress.revoke(certificate, adult("Équipe"), reason="Fraude")
    assert not revoked.is_valid
    with pytest.raises(errors.CertificateNotFound):
        progress.certificate_by_code("AAAA-BBBB-CCCC")


def test_the_certificate_pdf_has_its_code():
    from apps.academy.certificate import check_url, render

    student = adult("Awa", last_name="Dossou")
    free = course(trainer(), modules=(("M", 1),))
    enrollments.get_course(student, free)
    lesson = free.modules.first().lessons.first()
    progress.save_position(student, lesson, seconds=240, ended=True)
    certificate = Certificate.objects.get(enrollment__user=student)
    assert certificate.holder_name == "Awa Dossou"
    pdf = render(certificate, "fr")
    assert pdf.startswith(b"%PDF")
    assert check_url(certificate).endswith(f"/fr/certificat/{certificate.code}")
