"""Numbers of the trainer: students, how many finish, what the courses earned."""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.payments.models import Payment

from .models import Course, Enrollment

E = Enrollment.Status
EARNED = (Payment.Status.HELD, Payment.Status.RELEASED)


def course_stats(courses) -> dict:
    """Per course id: students, finished, completion rate, earned (after commission)."""
    rows = (
        Enrollment.objects.filter(course__in=courses, status=E.ACTIVE)
        .values("course_id")
        .annotate(
            students=Count("pk"),
            finished=Count("pk", filter=Q(completed_at__isnull=False)),
            earned=Coalesce(Sum("payment__items_minor", filter=Q(payment__status__in=EARNED)), 0)
            - Coalesce(Sum("payment__commission_minor", filter=Q(payment__status__in=EARNED)), 0),
        )
    )
    found = {row["course_id"]: row for row in rows}
    stats = {}
    for course in courses:
        row = found.get(course.pk, {})
        students = row.get("students", 0)
        finished = row.get("finished", 0)
        stats[course.pk] = {
            "students": students,
            "finished": finished,
            "completion_percent": round(finished * 100 / students) if students else 0,
            "earned_minor": int(row.get("earned", 0) or 0),
        }
    return stats


def trainer_courses(user, *, platform: bool = False):
    courses = Course.objects.select_related("cover", "trade", "country")
    courses = courses.filter(pro__isnull=True) if platform else courses.filter(pro__user=user)
    return list(courses.order_by("-created_at"))
