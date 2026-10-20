"""The availability engine, case by case (local times of a salon in Cotonou, Monday)."""

import datetime
import time
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, transaction

from apps.booking import availability, errors
from apps.booking.models import (
    Appointment,
    AppointmentStep,
    Resource,
    StaffBreak,
    StaffPeriod,
    StepResource,
    TimeOff,
)
from apps.booking.services import agenda, appointments
from apps.core.tests.factories import CountryFactory
from apps.messaging.tests.factories import adult
from apps.pros.models import Closure, ServiceOption

from .factories import MONDAY, NOW, at, local_times, person, salon, service

pytestmark = pytest.mark.django_db


def slots(pro, svc, day=MONDAY, **kwargs):
    return availability.day_slots(pro, svc, day, now=NOW, **kwargs)


def book(pro, svc, start, **kwargs):
    kwargs.setdefault("user", adult("Awa"))
    return appointments.book(pro, svc.pk, start, **kwargs)


def test_opening_hours_and_the_grid():
    pro = salon()
    svc = service(pro, ("work", 60))
    times = local_times(slots(pro, svc))
    assert times[0] == "09:00" and times[-1] == "17:00" and len(times) == 17
    assert "17:30" not in times  # would end after closing time


def test_a_lunch_break():
    pro = salon()
    owner = pro.staff.get()
    StaffBreak.objects.create(
        staff=owner, weekday=0, starts_at=datetime.time(12), ends_at=datetime.time(13)
    )
    times = local_times(slots(pro, service(pro, ("work", 60))))
    assert "11:00" in times and "11:30" not in times and "12:30" not in times
    assert "13:00" in times


def test_an_absence_and_a_closed_day():
    pro = salon()
    TimeOff.objects.create(pro=pro, starts_at=at(9), ends_at=at(12))
    svc = service(pro, ("work", 30))
    assert local_times(slots(pro, svc))[0] == "12:00"
    Closure.objects.create(pro=pro, starts_on=MONDAY, ends_on=MONDAY)
    availability.bump(pro.pk)
    assert slots(pro, svc) == []


def test_an_appointment_takes_its_time():
    pro = salon()
    svc = service(pro, ("work", 60))
    book(pro, svc, at(10))
    times = local_times(slots(pro, svc))
    assert "09:00" in times and "09:30" not in times and "10:00" not in times
    assert "10:30" not in times and "11:00" in times


def test_waiting_time_frees_the_person():
    # Colour: 30 min work, 60 min waiting, 30 min rinse. A first client at 9:00 leaves the
    # colourist free from 9:30 to 10:30: a second colour fits at 9:30.
    pro = salon()
    svc = service(pro, ("work", 30), ("wait", 60), ("work", 30))
    book(pro, svc, at(9))
    times = local_times(slots(pro, svc))
    assert "09:30" in times and "10:00" in times  # rinse 11:00 or 11:30, after the first one
    assert "10:30" not in times  # the first rinse (10:30-11:00) keeps the colourist
    second = book(pro, svc, at(9, 30), user=adult("Inès"))
    steps = list(second.steps.order_by("position"))
    assert steps[1].staff is None and steps[2].starts_at == at(11)


def test_another_person_takes_the_last_step():
    pro = salon()
    owner = pro.staff.get()
    helper = person(pro, "Carine")
    svc = service(pro, ("work", 30), ("wait", 30), ("work", 30, {"other_staff_ok": True}))
    # The owner is away during the last step; the helper is busy during the first one.
    TimeOff.objects.create(pro=pro, staff=owner, starts_at=at(10), ends_at=at(11))
    TimeOff.objects.create(pro=pro, staff=helper, starts_at=at(9), ends_at=at(9, 30))
    slot = availability.find(pro, svc, at(9))
    assert slot is not None
    assert slot.steps[0][5] == str(owner.pk) and slot.steps[2][5] == str(helper.pk)
    strict = service(pro, ("work", 30), ("wait", 30), ("work", 30), name="Strict")
    assert availability.find(pro, strict, at(9)) is None  # same person needed


def test_a_resource_in_use():
    pro = salon()
    person(pro, "Carine")
    chair = Resource.objects.create(pro=pro, name="Bac", quantity=1)
    svc = service(pro, ("work", 30), ("wait", 30))
    StepResource.objects.create(step=svc.steps.get(position=1), resource=chair)
    book(pro, svc, at(9))
    times = local_times(slots(pro, svc))
    assert "09:00" not in times  # two people free, but the only basin is taken 9:30-10:00
    assert "09:30" in times  # basin from 10:00
    chair.quantity = 2
    chair.save()
    availability.bump(pro.pk)
    assert "09:00" in local_times(slots(pro, svc))


def test_the_daily_limit():
    pro = salon()
    owner = pro.staff.get()
    owner.daily_limit = 1
    owner.save()
    svc = service(pro, ("work", 30))
    book(pro, svc, at(9))
    assert slots(pro, svc) == []
    assert local_times(slots(pro, svc, day=MONDAY + datetime.timedelta(days=1)))[0] == "09:00"


def test_notice_and_horizon():
    pro = salon()
    agenda.update_settings(pro, min_notice_minutes=120, horizon_days=3)
    svc = service(pro, ("work", 30))
    now = at(10)
    assert local_times(availability.day_slots(pro, svc, MONDAY, now=now))[0] == "12:00"
    far = MONDAY + datetime.timedelta(days=4)
    assert availability.day_slots(pro, svc, far, now=now) == []
    assert availability.day_slots(pro, svc, MONDAY + datetime.timedelta(days=3), now=now)


def test_summer_time_in_france():
    paris = ZoneInfo("Europe/Paris")
    france = CountryFactory(code="FR", name="France", phone_prefix="+33", timezone="Europe/Paris")
    pro = salon("Salon Paris", country=france, currency="EUR")
    svc = service(pro, ("work", 60))
    change_day = datetime.date(2030, 10, 27)  # summer time ends at 3:00
    found = availability.day_slots(pro, svc, change_day, now=NOW)
    assert found[0].start == datetime.datetime(2030, 10, 27, 9, tzinfo=paris)
    assert found[0].start.utcoffset() is None or found[0].start.astimezone(paris).hour == 9
    summer = availability.day_slots(pro, svc, datetime.date(2030, 7, 1), now=NOW)
    assert summer[0].start.astimezone(datetime.UTC).hour == 7  # 9:00 in Paris, summer


def test_anyone_takes_the_least_busy_person():
    pro = salon()
    owner = pro.staff.get()
    helper = person(pro, "Carine")
    svc = service(pro, ("work", 30))
    book(pro, svc, at(15), staff_id=owner.pk)
    slot = availability.find(pro, svc, at(9))
    assert slot.staff_id == str(helper.pk)


def test_options_make_it_longer():
    pro = salon()
    svc = service(pro, ("work", 60))
    longer = ServiceOption.objects.create(service=svc, name="Mèches", extra_minutes=60)
    times = local_times(slots(pro, svc, option_ids=[longer.pk]))
    assert times[-1] == "16:00"
    assert availability.find(pro, svc, at(16), option_ids=[longer.pk]).end == at(18)


def test_own_hours_and_allowed_services():
    pro = salon()
    owner = pro.staff.get()
    helper = person(pro, "Carine", own_hours=True)
    StaffPeriod.objects.create(
        staff=helper, weekday=0, starts_at=datetime.time(14), ends_at=datetime.time(20)
    )
    braids = service(pro, ("work", 60), name="Tresses")
    owner.services.set([service(pro, ("work", 30), name="Autre")])
    times = local_times(slots(pro, braids))
    assert times[0] == "14:00" and times[-1] == "19:00"  # only the helper does braids
    assert slots(pro, braids, staff_id=owner.pk) == []
    assert local_times(slots(pro, braids, staff_id=helper.pk))[0] == "14:00"


def test_the_cache_follows_every_change():
    pro = salon()
    svc = service(pro, ("work", 60))
    first = slots(pro, svc)
    TimeOff.objects.create(pro=pro, starts_at=at(9), ends_at=at(18))
    assert slots(pro, svc) == first  # cached: nothing told the engine
    agenda.add_time_off(pro, starts_at=at(9), ends_at=at(10))
    assert slots(pro, svc) == []


def test_no_double_booking():
    pro = salon()
    svc = service(pro, ("work", 60))
    book(pro, svc, at(10))
    with pytest.raises(errors.SlotTaken):
        book(pro, svc, at(10), user=adult("Inès"))
    first = Appointment.objects.get()
    step = first.steps.get()
    with pytest.raises(IntegrityError), transaction.atomic():
        AppointmentStep.objects.create(
            appointment=first,
            position=9,
            kind="work",
            starts_at=at(10, 30),
            ends_at=at(11),
            staff=step.staff,
        )


def test_a_group_together_then_one_after_the_other():
    pro = salon()
    person(pro, "Carine")
    svc = service(pro, ("work", 60))
    together = availability.group_plan(pro, svc, at(9), 2)
    assert [s.start for s in together] == [at(9), at(9)]
    in_a_row = availability.group_plan(pro, svc, at(9), 3)
    assert in_a_row is not None and [s.start for s in in_a_row] == [at(9), at(10), at(11)]
    assert availability.group_plan(pro, svc, at(17), 3) is None


def test_a_busy_salon_stays_fast():
    pro = salon(step=15)
    for index in range(9):
        person(pro, f"Coiffeuse {index}")
    svc = service(pro, ("work", 30), ("wait", 45), ("work", 30), ("work", 15))
    for index in range(20):
        book(pro, svc, at(9 + index % 8, 0), user=adult(f"Cliente {index}"))
    availability.bump(pro.pk)
    started = time.perf_counter()
    week = availability.week_slots(pro, svc, MONDAY, now=NOW)
    cold = time.perf_counter() - started
    started = time.perf_counter()
    availability.week_slots(pro, svc, MONDAY, now=NOW)
    warm = time.perf_counter() - started
    assert sum(len(day) for day in week.values()) > 100
    assert cold < 3 and warm < 0.2
