"""Small pieces shared by the services of the academy."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings
from django.db.models import Sum
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from apps.core.selectors import get_setting

from .. import errors, selectors
from ..models import Course, Lesson

SOURCE = "academy"
PASS_SOURCE = "academy_pass"  # noqa: S105 - a payment source, not a password
LINK = "/academie"
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: easy to read aloud


def setting(key: str, country, default):
    return get_setting(key, country=country, default=default)


def require_open(country) -> None:
    if not selectors.is_open(country):
        raise errors.AcademyClosed()


# Pages of the academy that a course link must never hide (/academie/<these>).
RESERVED = {"mes-formations", "pass", "lives", "live", "nouvelle"}


def unique_slug(title: str, *, exclude=None) -> str:
    base = slugify(title)[:60].strip("-") or "formation"
    if base in RESERVED:
        base = f"formation-{base}"
    slug = base
    rows = Course.objects.all()
    if exclude is not None:
        rows = rows.exclude(pk=exclude.pk)
    while rows.filter(slug=slug).exists():
        slug = f"{base}-{get_random_string(4, 'abcdefghjkmnpqrstuvwxyz23456789')}"
    return slug


def certificate_code() -> str:
    return "-".join("".join(secrets.choice(CODE_CHARS) for _ in range(4)) for _ in range(3))


def ip_hash(ip: str | None) -> str:
    if not ip:
        return ""
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"academy:{ip}".encode(), hashlib.sha256).hexdigest()


def lessons_of(course: Course):
    return Lesson.objects.filter(module__course=course).order_by(
        "module__position", "module__created_at", "position", "created_at"
    )


def refresh_duration(course: Course) -> None:
    """Total length, from the videos that are ready."""
    for lesson in lessons_of(course).select_related("video"):
        video = lesson.video
        seconds = int(video.duration_seconds or 0) if video is not None and video.is_ready else 0
        if seconds and seconds != lesson.duration_seconds:
            lesson.duration_seconds = seconds
            lesson.save(update_fields=["duration_seconds", "updated_at"])
    total = lessons_of(course).aggregate(total=Sum("duration_seconds"))["total"] or 0
    if total != course.duration_seconds:
        course.duration_seconds = total
        course.save(update_fields=["duration_seconds", "updated_at"])
