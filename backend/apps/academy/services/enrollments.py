"""A student gets a course: free, bought once (secure payment) or with the pass.

Bought once: the money is held until she opens the first lesson (then it goes to the trainer).
Before that, and within the withdrawal period, she can get her money back herself. At
checkout she ticks the waiver: she gives up the right to change her mind once she opens a
lesson (law on distance selling of digital content).
"""

from __future__ import annotations

import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from .. import errors, selectors
from ..models import Course, Enrollment
from .common import LINK, SOURCE, ip_hash, setting

E = Enrollment.Status
A = Enrollment.Access
PS = Payment.Status


def refund_days(course: Course) -> int:
    return int(setting("academy.refund_days", course.country, 14))


def _count(course: Course, delta: int) -> None:
    Course.objects.filter(pk=course.pk).update(students_count=F("students_count") + delta)


@transaction.atomic
def get_course(user, course: Course, *, waiver: bool = False, waiver_text: str = "", ip=None):
    """Returns (enrollment, payment page or None)."""
    from .common import require_open

    require_open(course.country)
    if course.status != Course.Status.PUBLISHED:
        raise errors.CourseNotFound()
    if selectors.is_trainer(user, course):
        raise errors.AlreadyEnrolled()
    enrollment = Enrollment.objects.select_for_update().filter(user=user, course=course).first()
    if (
        enrollment is not None
        and enrollment.status == E.ACTIVE
        and (enrollment.access != A.PASS or selectors.has_pass(user))
    ):
        raise errors.AlreadyEnrolled()
    pricing = course.pricing
    if pricing == Course.Pricing.FREE:
        return _active(enrollment, user, course, A.FREE), None
    if pricing == Course.Pricing.PASS:
        if not selectors.has_pass(user):
            raise errors.PassRequired()
        return _active(enrollment, user, course, A.PASS), None
    if not can_purchase(user):
        raise errors.CannotBuy()
    if not waiver or not (waiver_text or "").strip():
        raise errors.WaiverRequired()
    if enrollment is None:
        enrollment = Enrollment(user=user, course=course, access=A.PURCHASE, status=E.WAITING)
    elif enrollment.status != E.WAITING:
        enrollment.status = E.WAITING
        enrollment.access = A.PURCHASE
        enrollment.payment = None
    enrollment.waiver_at = timezone.now()
    enrollment.waiver_text = waiver_text.strip()[:1000]
    enrollment.waiver_ip_hash = ip_hash(ip)
    enrollment.save()
    payment = enrollment.payment
    if payment is None or payment.status != PS.PENDING_PAYMENT:
        payment = payment_services.create_payment(
            user,
            selectors.seller_of(course),
            purpose=Purpose.TRAINING,
            items_minor=course.price_minor,
            currency=course.currency,
            description=course.title[:200],
            delivery_mode=Payment.Delivery.SERVICE,
            source_type=SOURCE,
            source_id=enrollment.pk,
        )
        enrollment.payment = payment
        enrollment.save(update_fields=["payment", "updated_at"])
    record("academy.checkout", enrollment, actor=user)
    payment = payment_services.start_checkout(payment, buyer=user)
    return enrollment, payment.checkout_url


def _active(enrollment, user, course: Course, access: str) -> Enrollment:
    new = enrollment is None or enrollment.status != E.ACTIVE
    if enrollment is None:
        enrollment = Enrollment(user=user, course=course)
    enrollment.access = access
    enrollment.status = E.ACTIVE
    enrollment.save()
    if new:
        _count(course, 1)
    record("academy.enrolled", enrollment, actor=user, metadata={"access": access})
    return enrollment


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True  # nothing was given before the payment


def on_payment_change(payment: Payment) -> None:
    with transaction.atomic():
        enrollment = (
            Enrollment.objects.select_for_update(of=("self",))
            .select_related("course__pro__user", "user")
            .filter(payment=payment)
            .first()
        )
        if enrollment is None:
            return
        if payment.status == PS.HELD and enrollment.status == E.WAITING:
            enrollment.status = E.ACTIVE
            enrollment.save(update_fields=["status", "updated_at"])
            _count(enrollment.course, 1)
            _paid(enrollment, payment)
        elif payment.status == PS.REFUNDED and enrollment.status == E.ACTIVE:
            enrollment.status = E.REFUNDED
            enrollment.save(update_fields=["status", "updated_at"])
            _count(enrollment.course, -1)


def _paid(enrollment: Enrollment, payment: Payment) -> None:
    course = enrollment.course
    student = enrollment.user
    _receipt(enrollment, payment)
    title, slug = course.title, course.slug
    transaction.on_commit(
        lambda: notify(student, "academy.course_ready", {"course": title}, link=f"{LINK}/{slug}")
    )
    if course.pro_id:
        trainer = course.pro.user
        name = student.first_name or ""
        transaction.on_commit(
            lambda: notify(
                trainer,
                "academy.course_sold",
                {"course": title, "student": name},
                link="/pro/academy",
            )
        )


def _receipt(enrollment: Enrollment, payment: Payment) -> None:
    from apps.invoicing import services as invoicing

    course = enrollment.course
    issuer = invoicing.issuer_for(course.pro) if course.pro_id else invoicing.platform_issuer()
    student = enrollment.user
    invoicing.issue_once(
        issuer,
        "invoice",
        source_type=SOURCE,
        source_id=payment.pk,
        buyer_name=student.first_name or str(student.phone or student.email or ""),
        buyer_user=student,
        lines=[{"label": course.title[:200], "quantity": 1, "unit_minor": payment.items_minor}],
        currency=payment.currency,
        paid_with=payment.reference,
    )


def started(enrollment: Enrollment) -> None:
    """She opens a lesson for the first time: the waiver applies, the money goes on."""
    if enrollment.started_at is not None:
        return
    enrollment.started_at = timezone.now()
    enrollment.save(update_fields=["started_at", "updated_at"])
    payment = enrollment.payment
    if payment is not None and payment.status == PS.HELD:
        payment_services.release(payment, reason="course_started")


@transaction.atomic
def refund(enrollment: Enrollment, user) -> Enrollment:
    """Within the withdrawal period, while no lesson was opened: the money comes back."""
    enrollment = (
        Enrollment.objects.select_for_update(of=("self",))
        .select_related("payment", "course__country")
        .get(pk=enrollment.pk)
    )
    if enrollment.user_id != user.pk:
        raise errors.NotEnrolled()
    days = refund_days(enrollment.course)
    payment = enrollment.payment
    paid_at = payment.paid_at if payment is not None else None
    if (
        enrollment.access != A.PURCHASE
        or enrollment.status != E.ACTIVE
        or enrollment.started_at is not None
        or payment is None
        or payment.status != PS.HELD
        or paid_at is None
        or timezone.now() > paid_at + datetime.timedelta(days=days)
    ):
        raise errors.RefundClosed(details={"days": days})
    payment_services.refund_full(payment, actor=user, reason="course_withdrawal")
    record("academy.refunded", enrollment, actor=user)
    return Enrollment.objects.get(pk=enrollment.pk)


def release_unstarted(now=None) -> int:
    """After the withdrawal period, a course never opened is paid to the trainer anyway."""
    now = now or timezone.now()
    count = 0
    rows = Enrollment.objects.filter(
        access=A.PURCHASE,
        status=E.ACTIVE,
        started_at__isnull=True,
        payment__status=PS.HELD,
    ).select_related("payment", "course__country")
    for enrollment in rows:
        payment = enrollment.payment
        days = refund_days(enrollment.course)
        if payment.paid_at and payment.paid_at + datetime.timedelta(days=days) <= now:
            payment_services.release(payment, reason="course_withdrawal_period_over")
            count += 1
    return count
