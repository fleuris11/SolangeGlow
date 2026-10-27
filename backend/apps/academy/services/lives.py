"""Training lives: a trainer plans a session, students register, reminders the day before
and just before, a waiting room that opens a few minutes before the start. The broadcast
goes through LiveProvider (not connected yet)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.models import Country
from apps.core.providers.base import ProviderNotConfigured
from apps.notifications.services import notify

from .. import errors, selectors
from ..live import live_provider
from ..models import Course, CourseLanguage, Enrollment, LiveRegistration, LiveSession
from .common import setting

L = LiveSession.Status


def _link(live: LiveSession) -> str:
    return f"/academie/live/{live.pk}"


def _check_open(country) -> None:
    if not selectors.is_open(country) or not selectors.lives_open(country):
        raise errors.LivesClosed()


def _validate(values: dict, now) -> None:
    title = (values.get("title") or "").strip()
    starts_at = values.get("starts_at")
    duration = values.get("duration_minutes")
    capacity = values.get("capacity")
    if (
        not title
        or len(title) > 120
        or starts_at is None
        or starts_at <= now
        or type(duration) is not int
        or not 15 <= duration <= 240
        or type(capacity) is not int
        or not 1 <= capacity <= 10_000
        or values.get("language", "fr") not in CourseLanguage.values
    ):
        raise errors.InvalidLive()


@transaction.atomic
def plan_live(user, *, platform: bool = False, country: str = "", course_id=None, **values):
    now = timezone.now()
    if platform:
        if not selectors.can_manage_platform(user):
            raise errors.NotTrainer()
        place = Country.objects.filter(code=country).first()
        pro = None
    else:
        from apps.pros.services import get_pro

        pro = get_pro(user)
        place = pro.country
    if place is None:
        raise errors.InvalidLive()
    _check_open(place)
    _validate(values, now)
    course = None
    if course_id:
        course = Course.objects.filter(pk=course_id).select_related("pro").first()
        if course is None or not selectors.is_trainer(user, course):
            raise errors.InvalidLive()
    live = LiveSession.objects.create(
        pro=pro,
        author=user,
        country=place,
        course=course,
        title=values["title"].strip(),
        description=(values.get("description") or "").strip()[:2000],
        language=values.get("language", "fr"),
        starts_at=values["starts_at"],
        duration_minutes=values["duration_minutes"],
        capacity=values["capacity"],
    )
    record("academy.live_planned", live, actor=user)
    if course is not None:
        _invite(live, course)
    return live


def _invite(live: LiveSession, course: Course) -> None:
    """The students of the course get an invitation."""
    students = list(
        Enrollment.objects.filter(course=course, status=Enrollment.Status.ACTIVE).select_related(
            "user"
        )
    )
    when = timezone.localtime(live.starts_at).isoformat()
    title, link = live.title, _link(live)
    for enrollment in students:
        transaction.on_commit(
            lambda u=enrollment.user: notify(
                u, "academy.live_invitation", {"live": title, "when": when}, link=link
            )
        )


def _own(user, live: LiveSession) -> None:
    if live.pro_id:
        if live.pro.user_id != user.pk:
            raise errors.NotTrainer()
    elif not selectors.can_manage_platform(user):
        raise errors.NotTrainer()


@transaction.atomic
def cancel_live(live: LiveSession, user) -> LiveSession:
    live = LiveSession.objects.select_for_update(of=("self",)).select_related("pro").get(pk=live.pk)
    _own(user, live)
    if live.status not in (L.SCHEDULED, L.LIVE):
        raise errors.LiveNotFound()
    live.status = L.CANCELLED
    live.save(update_fields=["status", "updated_at"])
    record("academy.live_cancelled", live, actor=user)
    title = live.title
    for registration in live.registrations.select_related("user"):
        transaction.on_commit(
            lambda u=registration.user: notify(
                u, "academy.live_cancelled", {"live": title}, link="/academie/lives"
            )
        )
    return live


def get_live(live_id) -> LiveSession:
    live = (
        LiveSession.objects.select_related("pro__user", "country", "course")
        .filter(pk=live_id)
        .first()
    )
    if live is None:
        raise errors.LiveNotFound()
    return live


@transaction.atomic
def register(user, live: LiveSession) -> LiveRegistration:
    live = LiveSession.objects.select_for_update().get(pk=live.pk)
    _check_open(live.country)
    if live.status not in (L.SCHEDULED, L.LIVE):
        raise errors.LiveNotFound()
    found = LiveRegistration.objects.filter(live=live, user=user).first()
    if found is not None:
        return found
    if live.registered_count >= live.capacity:
        raise errors.LiveFull()
    registration = LiveRegistration.objects.create(live=live, user=user)
    LiveSession.objects.filter(pk=live.pk).update(registered_count=F("registered_count") + 1)
    record("academy.live_registered", live, actor=user)
    return registration


@transaction.atomic
def unregister(user, live: LiveSession) -> None:
    deleted, _ = LiveRegistration.objects.filter(live=live, user=user).delete()
    if deleted:
        LiveSession.objects.filter(pk=live.pk, registered_count__gt=0).update(
            registered_count=F("registered_count") - 1
        )


def room_opens_at(live: LiveSession) -> datetime.datetime:
    minutes = int(setting("academy.live_room_open_minutes", live.country, 10))
    return live.starts_at - datetime.timedelta(minutes=minutes)


def room(user, live: LiveSession, now=None) -> dict:
    """The waiting room: how long before the start, whether she can come in."""
    now = now or timezone.now()
    host = _is_host(user, live)
    registered = host or LiveRegistration.objects.filter(live=live, user=user).exists()
    ends_at = live.starts_at + datetime.timedelta(minutes=live.duration_minutes)
    return {
        "live": live,
        "registered": registered,
        "host": host,
        "opens_at": room_opens_at(live),
        "ends_at": ends_at,
        "open": registered and room_opens_at(live) <= now < ends_at and live.status != L.CANCELLED,
        "seconds_left": max(0, int((live.starts_at - now).total_seconds())),
    }


def _is_host(user, live: LiveSession) -> bool:
    if live.pro_id:
        return live.pro.user_id == user.pk
    return selectors.can_manage_platform(user)


def join(user, live: LiveSession, now=None) -> str:
    """The link to the broadcast (when a provider is connected)."""
    state = room(user, live, now)
    if not state["registered"]:
        raise errors.LiveNotFound()
    if not state["open"]:
        minutes = int(setting("academy.live_room_open_minutes", live.country, 10))
        raise errors.LiveNotOpen(details={"minutes": minutes})
    try:
        provider = live_provider()
    except ProviderNotConfigured as exc:
        raise errors.BroadcastNotAvailable() from exc
    if not live.room:  # pragma: no cover - needs a provider (prompt 14)
        live.room = provider.create_room(live)
        live.save(update_fields=["room", "updated_at"])
    return provider.join_url(live, user, host=state["host"])  # pragma: no cover


# --- By itself (Celery Beat, every 5 minutes) ---------------------------------------------------


def send_reminders(now=None) -> int:
    """The day before and a few minutes before, once each."""
    now = now or timezone.now()
    count = 0
    rows = LiveRegistration.objects.filter(
        live__status=L.SCHEDULED, live__starts_at__gt=now
    ).select_related("live__country", "user")
    for registration in rows:
        live = registration.live
        day = int(setting("academy.live_reminder_hours", live.country, 24))
        soon = int(setting("academy.live_reminder_minutes", live.country, 15))
        left = live.starts_at - now
        field = None
        if left <= datetime.timedelta(minutes=soon) and registration.reminded_soon_at is None:
            field, event = "reminded_soon_at", "academy.live_starting"
        elif left <= datetime.timedelta(hours=day) and registration.reminded_day_at is None:
            field, event = "reminded_day_at", "academy.live_reminder"
        if field is None:
            continue
        setattr(registration, field, now)
        if field == "reminded_soon_at" and registration.reminded_day_at is None:
            registration.reminded_day_at = now  # registered at the last minute: one message
        registration.save(update_fields=["reminded_day_at", "reminded_soon_at", "updated_at"])
        when = timezone.localtime(live.starts_at).isoformat()
        notify(registration.user, event, {"live": live.title, "when": when}, link=_link(live))
        count += 1
    return count


def close_lives(now=None) -> int:
    """A live past its end is over."""
    now = now or timezone.now()
    count = 0
    for live in LiveSession.objects.filter(status__in=[L.SCHEDULED, L.LIVE], starts_at__lt=now):
        if live.starts_at + datetime.timedelta(minutes=live.duration_minutes) <= now:
            live.status = L.ENDED
            live.save(update_fields=["status", "updated_at"])
            count += 1
    return count
