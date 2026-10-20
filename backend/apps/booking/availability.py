"""Availability engine: the times a service can start, day by day, in the pro's time zone.

For each day and each staff member:
  working time = her own hours (or the salon's) - salon closures - her breaks
                 - absences, holidays and blocked ranges - the *work* steps of the
                 appointments that keep their time.
Waiting steps (a colour that acts) do not keep the person: she can take another client.
A step may need a resource (chair, room) held for the whole step, waiting included.

A start time is possible when every step, chained one after the other, finds its person
(the chosen one; or « anyone »: the same person as before when possible, otherwise someone
else if the step allows it, the least busy first) and its resource, without going over a
person's daily limit. Times are offered every `slot_step_minutes`, from the minimum notice
up to the horizon.

The raw slots of a day are cached; any change for the pro bumps its version (bump()),
which makes every cached day of this pro obsolete. The notice is applied after the cache.
"""

from __future__ import annotations

import bisect
import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.utils import timezone

from apps.core.selectors import get_setting
from apps.pros.hours import zone_of
from apps.pros.models import ProProfile, Service, ServiceStep

from .models import Appointment, AppointmentStep, BookingSettings, StaffMember, TimeOff

WORK = ServiceStep.Kind.WORK
MINUTE = 60
CACHE_SECONDS = 15 * 60


# --- What a service needs -------------------------------------------------------------------------


@dataclass(frozen=True)
class StepNeed:
    position: int
    kind: str
    label: str
    minutes: int
    needs_staff: bool
    other_staff_ok: bool
    resource_id: object = None


def needs_of(service: Service, option_ids=()) -> list[StepNeed]:
    """The chained steps of a service; options add their time to the last work step."""
    steps = list(service.steps.all().select_related("resource_need"))
    needs = []
    for step in steps:
        resource = getattr(step, "resource_need", None)
        needs.append(
            StepNeed(
                position=step.position,
                kind=step.kind,
                label=step.label,
                minutes=step.duration_minutes,
                needs_staff=step.kind == WORK and step.needs_staff,
                other_staff_ok=step.other_staff_ok,
                resource_id=resource.resource_id if resource else None,
            )
        )
    if not needs:
        needs = [StepNeed(0, WORK, "", max(service.duration_minutes, 15), True, False)]
    extra = sum(
        o.extra_minutes for o in service.options.all() if str(o.pk) in {str(i) for i in option_ids}
    )
    if extra:
        index = max((i for i, n in enumerate(needs) if n.kind == WORK), default=len(needs) - 1)
        n = needs[index]
        needs[index] = StepNeed(
            n.position,
            n.kind,
            n.label,
            n.minutes + extra,
            n.needs_staff,
            n.other_staff_ok,
            n.resource_id,
        )
    return needs


# --- Settings of the pro ------------------------------------------------------------------------


def settings_of(pro: ProProfile) -> BookingSettings:
    found = getattr(pro, "_booking_settings", None)
    if found is None:
        found, _ = BookingSettings.objects.get_or_create(pro=pro)
        pro._booking_settings = found
    return found


def min_notice(pro: ProProfile) -> datetime.timedelta:
    own = settings_of(pro).min_notice_minutes
    minutes = (
        own
        if own is not None
        else get_setting("booking.min_notice_minutes", country=pro.country, default=120)
    )
    return datetime.timedelta(minutes=int(minutes))


def horizon(pro: ProProfile) -> int:
    own = settings_of(pro).horizon_days
    return int(
        own
        if own is not None
        else get_setting("booking.horizon_days", country=pro.country, default=60)
    )


# --- Cache version -------------------------------------------------------------------------------


def _version_key(pro_id) -> str:
    return f"booking:version:{pro_id}"


def version(pro_id) -> int:
    value = cache.get(_version_key(pro_id))
    if value is None:
        value = 1
        cache.set(_version_key(pro_id), value, None)
    return int(value)


def bump(pro_id) -> None:
    """Something changed in this agenda: every cached day of the pro is obsolete."""
    try:
        cache.incr(_version_key(pro_id))
    except ValueError:
        cache.set(_version_key(pro_id), 2, None)


# --- Intervals -----------------------------------------------------------------------------------


def _subtract(windows: list[tuple[int, int]], cut: tuple[int, int]) -> list[tuple[int, int]]:
    a, b = cut
    result = []
    for start, end in windows:
        if b <= start or a >= end:
            result.append((start, end))
            continue
        if start < a:
            result.append((start, a))
        if b < end:
            result.append((b, end))
    return result


def _merge(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _fits(free: list[tuple[int, int]], start: int, end: int) -> bool:
    index = bisect.bisect_right(free, (start, float("inf"))) - 1
    return index >= 0 and free[index][0] <= start and end <= free[index][1]


def _ts(moment: datetime.datetime) -> int:
    return int(moment.timestamp())


# --- One day -------------------------------------------------------------------------------------


@dataclass
class DayContext:
    """Everything needed to place appointments on one local day."""

    day: datetime.date
    zone: object
    free: dict  # staff id -> sorted free intervals (timestamps)
    load: dict  # staff id -> appointments that day
    limits: dict  # staff id -> daily limit or None
    allowed: dict  # staff id -> set of service ids (empty: all)
    order: list  # staff ids in display order
    resources: dict  # resource id -> (capacity, [(start, end)])
    extra_busy: dict = field(default_factory=lambda: defaultdict(list))


def _local(day: datetime.date, moment: datetime.time, zone) -> int:
    return _ts(datetime.datetime.combine(day, moment, tzinfo=zone))


def day_context(
    pro: ProProfile, day: datetime.date, *, ignore_appointment=None, appointments: bool = True
) -> DayContext:
    """`appointments=False`: the open time only (for the occupancy of the dashboard)."""
    zone = zone_of(pro)
    day_start = datetime.datetime.combine(day, datetime.time.min, tzinfo=zone)
    day_end = day_start + datetime.timedelta(days=1)
    staff = list(
        StaffMember.objects.filter(pro=pro, is_active=True).prefetch_related(
            "periods", "breaks", "services"
        )
    )
    salon_periods = [
        (p.opens_at, p.closes_at) for p in pro.opening_periods.all() if p.weekday == day.weekday()
    ]
    closed = any(c.starts_on <= day <= c.ends_on for c in pro.closures.all())
    time_off = list(TimeOff.objects.filter(pro=pro, starts_at__lt=day_end, ends_at__gt=day_start))
    busy_steps = AppointmentStep.objects.filter(
        appointment__pro=pro,
        blocking=True,
        starts_at__lt=day_end,
        ends_at__gt=day_start,
    )
    if ignore_appointment is not None:
        busy_steps = busy_steps.exclude(appointment_id=ignore_appointment)
    busy_steps = list(busy_steps.values("staff_id", "resource_id", "kind", "starts_at", "ends_at"))

    loads = (
        AppointmentStep.objects.filter(
            appointment__pro=pro,
            appointment__status__in=Appointment.BLOCKING,
            appointment__starts_at__gte=day_start,
            appointment__starts_at__lt=day_end,
            staff__isnull=False,
        )
        .exclude(appointment_id=ignore_appointment)
        .values("staff_id")
        .annotate(n=Count("appointment_id", distinct=True))
    )
    load = {row["staff_id"]: row["n"] for row in loads}

    free = {}
    for member in staff:
        if closed:
            free[member.pk] = []
            continue
        periods = (
            [(p.starts_at, p.ends_at) for p in member.periods.all() if p.weekday == day.weekday()]
            if member.own_hours
            else salon_periods
        )
        windows = _merge(
            [(_local(day, start, zone), _local(day, end, zone)) for start, end in periods]
        )
        for pause in member.breaks.all():
            if pause.weekday == day.weekday():
                windows = _subtract(
                    windows, (_local(day, pause.starts_at, zone), _local(day, pause.ends_at, zone))
                )
        for off in time_off:
            if off.staff_id in (None, member.pk):
                windows = _subtract(windows, (_ts(off.starts_at), _ts(off.ends_at)))
        for step in busy_steps if appointments else ():
            if step["staff_id"] == member.pk and step["kind"] == WORK:
                windows = _subtract(windows, (_ts(step["starts_at"]), _ts(step["ends_at"])))
        free[member.pk] = windows

    from .models import Resource

    resources = {r.pk: (r.quantity, []) for r in Resource.objects.filter(pro=pro, is_active=True)}
    for step in busy_steps:
        if step["resource_id"] in resources:
            resources[step["resource_id"]][1].append((_ts(step["starts_at"]), _ts(step["ends_at"])))
    return DayContext(
        day=day,
        zone=zone,
        free=free,
        load=load,
        limits={m.pk: m.daily_limit for m in staff},
        allowed={m.pk: {s.pk for s in m.services.all()} for m in staff},
        order=[m.pk for m in staff],
        resources=resources,
    )


@dataclass(frozen=True)
class PlannedStep:
    position: int
    kind: str
    label: str
    start: int
    end: int
    staff_id: object
    resource_id: object


def _resource_free(ctx: DayContext, resource_id, start: int, end: int, planned) -> bool:
    if resource_id is None:
        return True
    if resource_id not in ctx.resources:
        return False
    capacity, used = ctx.resources[resource_id]
    taken = [(a, b) for a, b in used] + [
        (p.start, p.end) for p in planned if p.resource_id == resource_id
    ]
    return sum(1 for a, b in taken if a < end and start < b) < capacity


def _staff_ok(ctx: DayContext, staff_id, service_id, start: int, end: int, planned) -> bool:
    allowed = ctx.allowed.get(staff_id)
    if allowed is None or (allowed and service_id not in allowed):
        return False
    if not _fits(ctx.free.get(staff_id, []), start, end):
        return False
    for a, b in ctx.extra_busy.get(staff_id, []):
        if a < end and start < b:
            return False
    limit = ctx.limits.get(staff_id)
    already = any(p.staff_id == staff_id for p in planned)
    return limit is None or ctx.load.get(staff_id, 0) + (0 if already else 1) <= limit


def _place(ctx, service_id, needs, start: int, first_staff, chosen) -> list[PlannedStep] | None:
    planned: list[PlannedStep] = []
    cursor, previous = start, None
    for need in needs:
        end = cursor + need.minutes * MINUTE
        staff_id = None
        if need.needs_staff:
            if previous is None:
                candidates = [first_staff]
            elif chosen is not None or not need.other_staff_ok:
                candidates = [previous]
            else:
                others = sorted(
                    (s for s in ctx.order if s != previous), key=lambda s: ctx.load.get(s, 0)
                )
                candidates = [previous, *others]
            staff_id = next(
                (s for s in candidates if _staff_ok(ctx, s, service_id, cursor, end, planned)),
                None,
            )
            if staff_id is None:
                return None
            previous = staff_id
        if not _resource_free(ctx, need.resource_id, cursor, end, planned):
            return None
        planned.append(
            PlannedStep(
                need.position, need.kind, need.label, cursor, end, staff_id, need.resource_id
            )
        )
        cursor = end
    return planned


def plan_at(ctx: DayContext, service_id, needs, start: int, chosen=None):
    """The steps of an appointment starting at `start`, or None when it does not fit."""
    if chosen is not None:
        firsts = [chosen]
    else:
        firsts = sorted(ctx.order, key=lambda s: (ctx.load.get(s, 0), ctx.order.index(s)))
    if not any(n.needs_staff for n in needs):
        firsts = [None]
    for first in firsts:
        planned = _place(ctx, service_id, needs, start, first, chosen)
        if planned is not None:
            return planned
    return None


def _candidates(ctx: DayContext, step_minutes: int) -> list[int]:
    windows = [w for intervals in ctx.free.values() for w in intervals]
    if not windows:
        return []
    midnight = _local(ctx.day, datetime.time.min, ctx.zone)
    first = min(a for a, _ in windows)
    last = max(b for _, b in windows)
    step = step_minutes * MINUTE
    start = midnight + -(-(first - midnight) // step) * step  # rounded up on the grid
    return list(range(start, last, step))


def _raw_day(pro, service, day, *, staff_id, option_ids, ignore_appointment) -> list[dict]:
    needs = needs_of(service, option_ids)
    ctx = day_context(pro, day, ignore_appointment=ignore_appointment)
    if staff_id is not None and staff_id not in ctx.allowed:
        return []
    total = sum(n.minutes for n in needs) * MINUTE
    slots = []
    for start in _candidates(ctx, settings_of(pro).slot_step_minutes):
        planned = plan_at(ctx, service.pk, needs, start, chosen=staff_id)
        if planned is None:
            continue
        main = next((p.staff_id for p in planned if p.staff_id is not None), None)
        slots.append(
            {
                "start": start,
                "end": start + total,
                "staff": str(main) if main else None,
                "steps": [
                    [
                        p.position,
                        p.kind,
                        p.label,
                        p.start,
                        p.end,
                        str(p.staff_id) if p.staff_id else None,
                        str(p.resource_id) if p.resource_id else None,
                    ]
                    for p in planned
                ],
            }
        )
    return slots


# --- Public API ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Slot:
    start: datetime.datetime
    end: datetime.datetime
    staff_id: str | None
    steps: list
    discount_percent: int = 0


def _discount(pro, start: datetime.datetime, now: datetime.datetime) -> int:
    try:
        offer = pro.last_minute
    except ObjectDoesNotExist:
        return 0
    if not offer.is_active:
        return 0
    return offer.percent_off if start <= now + datetime.timedelta(hours=offer.window_hours) else 0


def day_slots(
    pro: ProProfile,
    service: Service,
    day: datetime.date,
    *,
    staff_id=None,
    option_ids=(),
    ignore_appointment=None,
    now: datetime.datetime | None = None,
    notice: bool = True,
) -> list[Slot]:
    """The possible starts of a service on a local day (cached, then filtered by time)."""
    now = now or timezone.now()
    staff_key = str(staff_id) if staff_id else "any"
    options_key = ",".join(sorted(str(o) for o in option_ids))
    raw = None
    key = None
    if ignore_appointment is None:
        key = (
            f"booking:slots:{pro.pk}:{version(pro.pk)}:{service.pk}:{options_key}:"
            f"{staff_key}:{day.isoformat()}"
        )
        raw = cache.get(key)
    if raw is None:
        raw = _raw_day(
            pro,
            service,
            day,
            staff_id=staff_id if staff_id is None else _as_uuid(staff_id),
            option_ids=option_ids,
            ignore_appointment=ignore_appointment,
        )
        if key:
            cache.set(key, raw, CACHE_SECONDS)
    earliest = now + (min_notice(pro) if notice else datetime.timedelta(0))
    last_day = (now.astimezone(zone_of(pro)) + datetime.timedelta(days=horizon(pro))).date()
    if day > last_day:
        return []
    result = []
    for item in raw:
        start = datetime.datetime.fromtimestamp(item["start"], tz=datetime.UTC)
        if start < earliest:
            continue
        result.append(
            Slot(
                start=start,
                end=datetime.datetime.fromtimestamp(item["end"], tz=datetime.UTC),
                staff_id=item["staff"],
                steps=item["steps"],
                discount_percent=_discount(pro, start, now),
            )
        )
    return result


def week_slots(pro, service, first_day: datetime.date, days: int = 7, **kwargs) -> dict:
    return {
        first_day + datetime.timedelta(days=i): day_slots(
            pro, service, first_day + datetime.timedelta(days=i), **kwargs
        )
        for i in range(days)
    }


def find(pro, service, start: datetime.datetime, *, staff_id=None, option_ids=(), **kwargs):
    """The slot that starts exactly at `start`, or None (recomputed, no cache)."""
    day = start.astimezone(zone_of(pro)).date()
    kwargs.setdefault("ignore_appointment", None)
    if kwargs["ignore_appointment"] is None:
        # A fresh look, as at the moment of booking.
        needs = needs_of(service, option_ids)
        ctx = day_context(pro, day)
        planned = plan_at(
            ctx, service.pk, needs, _ts(start), chosen=_as_uuid(staff_id) if staff_id else None
        )
        if planned is None:
            return None
        return _slot_from(planned, needs, start)
    for slot in day_slots(
        pro, service, day, staff_id=staff_id, option_ids=option_ids, notice=False, **kwargs
    ):
        if slot.start == start:
            return slot
    return None


def _slot_from(planned, needs, start) -> Slot:
    total = sum(n.minutes for n in needs) * MINUTE
    main = next((p.staff_id for p in planned if p.staff_id is not None), None)
    return Slot(
        start=start,
        end=datetime.datetime.fromtimestamp(_ts(start) + total, tz=datetime.UTC),
        staff_id=str(main) if main else None,
        steps=[
            [
                p.position,
                p.kind,
                p.label,
                p.start,
                p.end,
                str(p.staff_id) if p.staff_id else None,
                str(p.resource_id) if p.resource_id else None,
            ]
            for p in planned
        ],
    )


def _as_uuid(value):
    import uuid

    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def group_plan(pro, service, start: datetime.datetime, size: int, option_ids=()):
    """Several people at the same time (one person each), or one after the other.

    Returns a list of plans (one per person) or None.
    """
    day = start.astimezone(zone_of(pro)).date()
    needs = needs_of(service, option_ids)
    total = sum(n.minutes for n in needs) * MINUTE
    for together in (True, False):
        ctx = day_context(pro, day)
        plans, cursor = [], _ts(start)
        for _ in range(size):
            planned = plan_at(ctx, service.pk, needs, cursor)
            if planned is None:
                break
            plans.append(planned)
            for staff_id in {p.staff_id for p in planned if p.staff_id is not None}:
                ctx.load[staff_id] = ctx.load.get(staff_id, 0) + 1
            for step in planned:
                if step.staff_id is not None and step.kind == WORK:
                    ctx.extra_busy[step.staff_id].append((step.start, step.end))
                if step.resource_id is not None:
                    ctx.resources[step.resource_id][1].append((step.start, step.end))
            if not together:
                cursor += total
        if len(plans) == size:
            return [
                _slot_from(p, needs, datetime.datetime.fromtimestamp(p[0].start, tz=datetime.UTC))
                for p in plans
            ]
    return None


def open_minutes(pro, day: datetime.date) -> dict:
    """Minutes each person of the agenda can work on a day (hours - breaks - time off)."""
    ctx = day_context(pro, day, appointments=False)
    return {staff: sum(b - a for a, b in windows) // MINUTE for staff, windows in ctx.free.items()}


__all__ = [
    "Slot",
    "bump",
    "day_context",
    "day_slots",
    "find",
    "group_plan",
    "needs_of",
    "open_minutes",
    "plan_at",
    "week_slots",
]
