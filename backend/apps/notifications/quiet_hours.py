"""Quiet hours: no phone alert, WhatsApp or SMS at night, in the person's time zone."""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from apps.core.selectors import get_setting


def _parse(value: str) -> datetime.time:
    hours, minutes = value.split(":")
    return datetime.time(int(hours), int(minutes))


def window_for(user) -> tuple[datetime.time, datetime.time]:
    country = user.country.code if user.country_id else None
    default = get_setting(
        "notifications.quiet_hours", country=country, default={"start": "22:00", "end": "07:00"}
    )
    start = user.quiet_hours_start or _parse(default["start"])
    end = user.quiet_hours_end or _parse(default["end"])
    return start, end


def zone_for(user) -> ZoneInfo:
    name = user.country.timezone if user.country_id else settings.TIME_ZONE
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError):
        return ZoneInfo(settings.TIME_ZONE)


def next_allowed(user, moment: datetime.datetime | None = None) -> datetime.datetime:
    """`moment` if outside quiet hours, else the end of the quiet hours."""
    moment = moment or timezone.now()
    start, end = window_for(user)
    if start == end:
        return moment
    local = moment.astimezone(zone_for(user))
    now = local.time()
    crosses_midnight = start > end
    quiet = (now >= start or now < end) if crosses_midnight else (start <= now < end)
    if not quiet:
        return moment
    end_day = local.date()
    if crosses_midnight and now >= start:
        end_day += datetime.timedelta(days=1)
    wake = datetime.datetime.combine(end_day, end, tzinfo=local.tzinfo)
    return wake.astimezone(datetime.UTC)
