"""Salons, people, services and times for the booking tests.

Times are given as local times of the pro (Benin: UTC+1, no summer time) on a fixed
Monday far in the future, so the minimum notice never gets in the way.
"""

import datetime
from zoneinfo import ZoneInfo

from apps.booking import selectors
from apps.booking.models import BookingSettings, StaffMember
from apps.messaging.tests.factories import adult
from apps.pros.models import OpeningPeriod, Service, ServiceStep
from apps.pros.tests.factories import ProFactory

BENIN = ZoneInfo("Africa/Porto-Novo")
MONDAY = datetime.date(2030, 1, 7)  # a Monday
NOW = datetime.datetime(2030, 1, 6, 8, 0, tzinfo=BENIN)  # the day before


def at(hour: int, minute: int = 0, day: datetime.date = MONDAY, zone=BENIN):
    return datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=zone)


def salon(name="Salon Estelle", *, hours=((9, 0), (18, 0)), step=30, days=range(7), **kwargs):
    pro = ProFactory(business_name=name, user=adult(name.split()[0]), **kwargs)
    for weekday in days:
        OpeningPeriod.objects.create(
            pro=pro,
            weekday=weekday,
            opens_at=datetime.time(*hours[0]),
            closes_at=datetime.time(*hours[1]),
        )
    BookingSettings.objects.update_or_create(
        pro=pro, defaults={"slot_step_minutes": step, "min_notice_minutes": 0, "horizon_days": 3650}
    )
    selectors.owner_staff(pro)
    return pro


def person(pro, name="Fifamè", **kwargs) -> StaffMember:
    return StaffMember.objects.create(pro=pro, name=name, **kwargs)


def service(pro, *steps, name="Coloration", price=20_000, **kwargs) -> Service:
    """steps: ("work", 30), ("wait", 45, {"other_staff_ok": True})…"""
    created = Service.objects.create(
        pro=pro, name=name, price_minor=price, currency=pro.currency or "XOF", **kwargs
    )
    for position, step in enumerate(steps or (("work", 60),)):
        extra = step[2] if len(step) > 2 else {}
        ServiceStep.objects.create(
            service=created,
            position=position,
            kind=step[0],
            duration_minutes=step[1],
            needs_staff=step[0] == "work",
            **extra,
        )
    created.duration_minutes = sum(s[1] for s in steps or (("work", 60),))
    created.save(update_fields=["duration_minutes"])
    return created


def local_times(slots, zone=BENIN) -> list[str]:
    return [s.start.astimezone(zone).strftime("%H:%M") for s in slots]
