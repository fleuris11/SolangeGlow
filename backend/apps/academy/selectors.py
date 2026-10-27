"""Reads of the academy: what is open, who may watch what, the catalogue."""

from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.core.models import Country
from apps.core.selectors import get_setting, is_feature_enabled

from .models import AcademyPass, Course, Enrollment, LiveSession

C = Course.Status
E = Enrollment.Status


def _code(country) -> str:
    return getattr(country, "code", None) or str(country or "") or "BJ"


def is_open(country) -> bool:
    return is_feature_enabled("academy", country=country)


def lives_open(country) -> bool:
    return is_feature_enabled("lives", country=country)


def currency_of(country) -> str:
    if isinstance(country, Country):
        return country.default_currency.code
    found = Country.objects.select_related("default_currency").filter(code=_code(country)).first()
    return found.default_currency.code if found else "XOF"


def price_limits(country) -> tuple[int, int]:
    """Lowest and highest price of a course sold once (smallest unit of the currency)."""
    low, high = get_setting("academy.price_limits", country=country, default=[500, 25_000])
    return int(low), int(high)


def pass_price(country) -> int | None:
    """Price of a month of pass, or None when the pass is not offered in this country."""
    value = get_setting("academy.pass_price_minor", country=country, default=0)
    return int(value) or None


def house_account(country):
    """The platform as the seller of its own courses and of the pass (created the first time)."""
    code = _code(country)
    email = get_setting(
        "academy.house_email", country=country, default=f"academy.{code.lower()}@solangeglow.com"
    )
    User = get_user_model()
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            first_name="Solange Glow Académie",
            country=Country.objects.filter(code=code).first(),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def seller_of(course: Course):
    return course.pro.user if course.pro_id else house_account(course.country)


def trainer_name(course: Course) -> str:
    return course.pro.display_name if course.pro_id else "Solange Glow"


def is_trainer(user, course: Course) -> bool:
    """The pro of the course, or a member of the team for the platform's courses."""
    if user is None or not user.is_authenticated:
        return False
    if course.pro_id:
        return course.pro.user_id == user.pk
    return can_manage_platform(user)


def can_manage_platform(user) -> bool:
    return bool(
        user.is_authenticated
        and user.is_staff
        and (user.is_superuser or user.has_perm("academy.change_course"))
    )


def has_pass(user, now=None) -> bool:
    if user is None or not user.is_authenticated:
        return False
    now = now or timezone.now()
    return AcademyPass.objects.filter(
        user=user, status=AcademyPass.Status.ACTIVE, current_period_end__gt=now
    ).exists()


def pass_of(user) -> AcademyPass | None:
    return AcademyPass.objects.filter(user=user).select_related("renewal_payment").first()


def enrollment_of(user, course: Course) -> Enrollment | None:
    if user is None or not user.is_authenticated:
        return None
    return Enrollment.objects.filter(user=user, course=course).first()


def can_watch(user, course: Course, enrollment: Enrollment | None = None) -> bool:
    """Every lesson of the course (a free preview is open to everybody)."""
    if is_trainer(user, course):
        return True
    enrollment = enrollment or enrollment_of(user, course)
    if enrollment is None or enrollment.status != E.ACTIVE:
        return False
    if enrollment.access == Enrollment.Access.PASS:
        return has_pass(user)
    return True


def published() -> QuerySet[Course]:
    return Course.objects.filter(status=C.PUBLISHED)


def catalogue(
    country,
    *,
    q: str = "",
    trade: str = "",
    level: str = "",
    language: str = "",
    pricing: str = "",
) -> QuerySet[Course]:
    courses = published().filter(country__code=_code(country))
    if q:
        words = q.strip()
        courses = courses.filter(
            Q(title__icontains=words)
            | Q(summary__icontains=words)
            | Q(pro__business_name__icontains=words)
        )
    if trade:
        courses = courses.filter(trade__key=trade)
    if level:
        courses = courses.filter(level=level)
    if language:
        courses = courses.filter(language=language)
    if pricing:
        courses = courses.filter(pricing=pricing)
    return courses.select_related("pro__user", "cover", "trade", "country").order_by(
        "-published_at", "pk"
    )


def course_by_slug(slug: str, viewer=None) -> Course:
    from .errors import CourseNotFound

    course = (
        Course.objects.select_related("pro__user", "cover", "trade", "country", "author")
        .filter(slug=slug)
        .first()
    )
    if course is None:
        raise CourseNotFound()
    if course.status != C.PUBLISHED and not is_trainer(viewer, course):
        raise CourseNotFound()
    return course


def upcoming_lives(country, now=None) -> QuerySet[LiveSession]:
    now = now or timezone.now()
    return (
        LiveSession.objects.filter(
            country__code=_code(country),
            status__in=[LiveSession.Status.SCHEDULED, LiveSession.Status.LIVE],
            starts_at__gte=now - datetime.timedelta(hours=6),
        )
        .select_related("pro__user", "course")
        .order_by("starts_at")
    )
