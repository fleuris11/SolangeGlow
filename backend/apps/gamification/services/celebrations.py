"""The calendar of celebrations: the next big days of her country, and a reminder a few
days before (with the pros and the products of the moment)."""

from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone, translation

from apps.notifications.services import notify

from ..models import Celebration
from .common import setting


def next_date(celebration: Celebration, day: datetime.date) -> datetime.date | None:
    """The coming occurrence (today included), or None when a one-off day is past."""
    if not celebration.yearly:
        return celebration.date if celebration.date >= day else None
    for year in (day.year, day.year + 1):
        try:
            found = celebration.date.replace(year=year)
        except ValueError:  # 29 February
            found = datetime.date(year, 3, 1)
        if found >= day:
            return found
    return None  # pragma: no cover - next year is always ahead


def upcoming(country_code: str, day: datetime.date | None = None, *, limit: int | None = None):
    """[(celebration, date)] of the coming months for a country, the nearest first."""
    day = day or timezone.localdate()
    horizon = day + datetime.timedelta(days=int(setting("games.calendar_days", 365)))
    found = []
    for celebration in Celebration.objects.filter(is_active=True).select_related("trade"):
        if celebration.countries and country_code not in celebration.countries:
            continue
        when = next_date(celebration, day)
        if when is not None and when <= horizon:
            found.append((celebration, when))
    found.sort(key=lambda item: item[1])
    return found[:limit] if limit else found


def send_reminders(now=None) -> int:
    """Celery Beat, every morning: « Mother's day in 7 days » to the people of the country
    who keep these reminders."""
    day = timezone.localdate(now)
    User = get_user_model()
    sent = 0
    for celebration in Celebration.objects.filter(is_active=True):
        when = next_date(celebration, day)
        if when is None or when - datetime.timedelta(days=celebration.remind_days) != day:
            continue
        if celebration.reminded_for == when:
            continue
        Celebration.objects.filter(pk=celebration.pk).update(reminded_for=when)
        people = User.objects.filter(is_active=True, onboarded_at__isnull=False).exclude(
            glow__celebration_reminders=False
        )
        if celebration.countries:
            people = people.filter(country__code__in=celebration.countries)
        for person in people.iterator():
            with translation.override(person.preferred_language or "fr"):
                context = {
                    "name": celebration.name,
                    "days": celebration.remind_days,
                    "message": celebration.message,
                }
            notify(person, "glow.celebration", context, link="/fetes")
            sent += 1
    return sent
