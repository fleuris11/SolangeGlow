"""Opening hours: "open now", next opening, in the time zone of the pro's country."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Country

from .models import Closure, OpeningPeriod, ProProfile


def zone_of(pro: ProProfile) -> ZoneInfo:
    name = pro.country.timezone if pro.country_id else settings.TIME_ZONE
    return ZoneInfo(name)


@dataclass(frozen=True)
class OpeningStatus:
    is_open: bool
    closes_at: datetime.datetime | None  # when open
    next_opening: datetime.datetime | None  # when closed (within two weeks)
    closed_today: bool  # exceptional closure today
    has_hours: bool


def _closed_on(closures, day: datetime.date) -> bool:
    return any(c.starts_on <= day <= c.ends_on for c in closures)


def opening_status(pro: ProProfile, at: datetime.datetime | None = None) -> OpeningStatus:
    """Uses prefetched `opening_periods` and `closures` when available."""
    zone = zone_of(pro)
    now = (at or timezone.now()).astimezone(zone)
    periods = list(pro.opening_periods.all())
    closures = list(pro.closures.all())
    if not periods:
        return OpeningStatus(False, None, None, False, False)

    today = now.date()
    closed_today = _closed_on(closures, today)
    if not closed_today:
        for period in periods:
            if (
                period.weekday == today.weekday()
                and period.opens_at <= now.time() < period.closes_at
            ):
                closes = datetime.datetime.combine(today, period.closes_at, tzinfo=zone)
                return OpeningStatus(True, closes, None, False, True)

    for offset in range(15):
        day = today + datetime.timedelta(days=offset)
        if _closed_on(closures, day):
            continue
        for period in sorted(periods, key=lambda p: p.opens_at):
            if period.weekday != day.weekday():
                continue
            start = datetime.datetime.combine(day, period.opens_at, tzinfo=zone)
            if start > now:
                return OpeningStatus(False, None, start, closed_today, True)
    return OpeningStatus(False, None, None, closed_today, True)


def open_now_q(at: datetime.datetime | None = None) -> Q:
    """Filter of the pros open at this moment, each in the time zone of her country."""
    moment = at or timezone.now()
    condition = Q(pk__in=[])
    zones = {c.pk: c.timezone for c in Country.objects.all()}
    zones[None] = settings.TIME_ZONE
    for country_id, zone_name in zones.items():
        local = moment.astimezone(ZoneInfo(zone_name))
        open_ids = OpeningPeriod.objects.filter(
            weekday=local.weekday(), opens_at__lte=local.time(), closes_at__gt=local.time()
        ).values("pro_id")
        closed_ids = Closure.objects.filter(
            starts_on__lte=local.date(), ends_on__gte=local.date()
        ).values("pro_id")
        in_country = Q(country__isnull=True) if country_id is None else Q(country_id=country_id)
        condition |= in_country & Q(pk__in=open_ids) & ~Q(pk__in=closed_ids)
    return condition
