"""Training lives in the live room (ADR-013): the trainer broadcasts, the registered
students watch, write questions and raise their hand; the replay is for them only."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.live import registry
from apps.notifications.services import notify

from . import selectors
from .models import LiveRegistration, LiveSession
from .services.common import setting

L = LiveSession.Status


def room_link(live_id) -> str:
    return f"/live/training/{live_id}"


def _planned(live: LiveSession) -> registry.Planned:
    host = live.pro.user if live.pro_id else live.author
    cover = ""
    if live.course_id and live.course.cover_id and live.course.cover.is_ready:
        from apps.core.media.services import variant_url

        cover = variant_url(live.course.cover, "medium") or ""
    return registry.Planned(
        source_id=live.pk,
        title=live.title,
        host=host,
        pro=live.pro,
        country=live.country,
        starts_at=live.starts_at,
        ends_at=live.starts_at + datetime.timedelta(minutes=live.duration_minutes),
        cancelled=live.status == L.CANCELLED,
        link=f"/academie/live/{live.pk}",
        cover_url=cover,
    )


def _registered(live_id):
    return LiveRegistration.objects.filter(live_id=live_id).select_related("user")


class TrainingLives(registry.LiveSource):
    kind = "training"
    hands = True
    guests = False

    def _get(self, source_id):
        return (
            LiveSession.objects.select_related(
                "pro__user", "pro__photo", "author", "country", "course__cover"
            )
            .filter(pk=source_id)
            .first()
        )

    def planned(self, source_id):
        live = self._get(source_id)
        return _planned(live) if live else None

    def can_watch(self, user, source_id) -> bool:
        if user is None or not user.is_authenticated:
            return False
        return LiveRegistration.objects.filter(live_id=source_id, user=user).exists()

    def replay_days(self, country) -> int:
        return int(setting("academy.live_replay_days", country, 30))

    def started(self, source_id, room) -> None:
        live = self._get(source_id)
        if live is None:
            return
        LiveSession.objects.filter(pk=live.pk).update(status=L.LIVE, updated_at=timezone.now())
        for registration in _registered(live.pk):
            transaction.on_commit(
                lambda u=registration.user: notify(
                    u, "academy.live_on_air", {"live": live.title}, link=room_link(live.pk)
                )
            )

    def ended(self, source_id, room) -> None:
        LiveSession.objects.filter(pk=source_id, status__in=[L.SCHEDULED, L.LIVE]).update(
            status=L.ENDED, updated_at=timezone.now()
        )

    def replay_ready(self, source_id, room) -> None:
        for registration in _registered(source_id):
            notify(
                registration.user,
                "academy.live_replay",
                {"live": room.title},
                link=room_link(source_id),
            )

    def upcoming(self, country, now, limit: int):
        if country is None or not (selectors.is_open(country) and selectors.lives_open(country)):
            return []
        rows = selectors.upcoming_lives(country, now).select_related(
            "author", "country", "course__cover", "pro__photo"
        )
        return [
            _planned(live)
            for live in rows[: limit * 2]
            if live.starts_at + datetime.timedelta(minutes=live.duration_minutes) > now
        ][:limit]

    def count_in_month(self, pro, start, end) -> int:
        return (
            LiveSession.objects.filter(pro=pro, starts_at__gte=start, starts_at__lt=end)
            .exclude(status=L.CANCELLED)
            .count()
        )
