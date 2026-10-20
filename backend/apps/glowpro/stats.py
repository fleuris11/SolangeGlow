"""The pro's dashboard, computed on the server for a period of local days.

Free: turnover and appointments of the month. Premium: everything else (occupancy,
average basket, per person and per service, new and loyal clients, the period before).
Turnover = the price of the done appointments; collected = what was really paid (online
through the secure payment, and at the salon).
"""

from __future__ import annotations

import datetime
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Min, Q, Sum

from apps.booking import availability
from apps.booking.models import Appointment, AppointmentStep, StaffMember
from apps.payments.models import Payment
from apps.pros.hours import zone_of
from apps.salon.models import OnSitePayment

from . import selectors
from .models import Feature

A = Appointment.Status
MAX_DAYS = 92


def _bounds(pro, start: datetime.date, end: datetime.date):
    zone = zone_of(pro)
    since = datetime.datetime.combine(start, datetime.time.min, tzinfo=zone)
    until = datetime.datetime.combine(
        end + datetime.timedelta(days=1), datetime.time.min, tzinfo=zone
    )
    return since, until, zone


def _client_key(appointment: dict):
    return (
        ("c", appointment["client_id"])
        if appointment["client_id"]
        else ("p", appointment["client_phone"])
    )


def _money(pro, since, until) -> dict:
    done = Appointment.objects.filter(
        pro=pro, status=A.COMPLETED, starts_at__gte=since, starts_at__lt=until
    )
    turnover = done.aggregate(total=Sum("price_minor"))["total"] or 0
    count = done.count()
    on_site = (
        OnSitePayment.objects.filter(
            pro=pro, cancelled_at__isnull=True, created_at__gte=since, created_at__lt=until
        ).aggregate(total=Sum("amount_minor"))["total"]
        or 0
    )
    online = (
        Payment.objects.filter(
            seller=pro.user,
            status__in=[Payment.Status.HELD, Payment.Status.RELEASED],
            created_at__gte=since,
            created_at__lt=until,
        ).aggregate(total=Sum("items_minor"))["total"]
        or 0
    )
    return {
        "turnover_minor": turnover,
        "collected_minor": on_site + online,
        "collected_online_minor": online,
        "collected_on_site_minor": on_site,
        "appointments": count,
        "average_minor": turnover // count if count else 0,
    }


def _occupancy(pro, start: datetime.date, end: datetime.date, since, until) -> tuple[int, dict]:
    open_minutes: dict = defaultdict(int)
    day = start
    while day <= end:
        for staff, minutes in availability.open_minutes(pro, day).items():
            open_minutes[staff] += minutes
        day += datetime.timedelta(days=1)
    booked: dict = defaultdict(int)
    for step in AppointmentStep.objects.filter(
        appointment__pro=pro,
        appointment__status__in=[*Appointment.BLOCKING, A.COMPLETED],
        kind="work",
        staff__isnull=False,
        starts_at__gte=since,
        starts_at__lt=until,
    ).values("staff_id", "starts_at", "ends_at"):
        booked[step["staff_id"]] += int((step["ends_at"] - step["starts_at"]).total_seconds() // 60)
    total_open = sum(open_minutes.values())
    total_booked = sum(min(booked[s], open_minutes[s]) for s in open_minutes)
    rate = round(100 * total_booked / total_open) if total_open else 0
    per_staff = {
        s: {
            "open_minutes": open_minutes[s],
            "booked_minutes": booked[s],
            "occupancy": round(100 * min(booked[s], open_minutes[s]) / open_minutes[s])
            if open_minutes[s]
            else 0,
        }
        for s in set(open_minutes) | set(booked)
    }
    return rate, per_staff


def _series(pro, start: datetime.date, end: datetime.date, done, zone) -> list[dict]:
    weekly = (end - start).days > 31
    buckets: dict = {}
    day = start
    while day <= end:
        key = day - datetime.timedelta(days=day.weekday()) if weekly else day
        buckets.setdefault(key, {"turnover_minor": 0, "appointments": 0})
        day += datetime.timedelta(days=1)
    for row in done:
        local = row["starts_at"].astimezone(zone).date()
        key = local - datetime.timedelta(days=local.weekday()) if weekly else local
        if key in buckets:
            buckets[key]["turnover_minor"] += row["price_minor"] or 0
            buckets[key]["appointments"] += 1
    return [{"day": k.isoformat(), **v} for k, v in sorted(buckets.items())]


def basic(pro, today: datetime.date) -> dict:
    start = today.replace(day=1)
    since, until, _zone = _bounds(pro, start, today)
    money = _money(pro, since, until)
    return {
        "start": start.isoformat(),
        "end": today.isoformat(),
        "turnover_minor": money["turnover_minor"],
        "appointments": money["appointments"],
    }


def complete(pro, start: datetime.date, end: datetime.date) -> dict:
    end = min(end, start + datetime.timedelta(days=MAX_DAYS - 1))
    key = f"glowpro:dash:{pro.pk}:{availability.version(pro.pk)}:{start}:{end}"
    found = cache.get(key)
    if found is not None:
        return found
    since, until, zone = _bounds(pro, start, end)
    money = _money(pro, since, until)
    rate, per_staff = _occupancy(pro, start, end, since, until)
    done = list(
        Appointment.objects.filter(
            pro=pro, status=A.COMPLETED, starts_at__gte=since, starts_at__lt=until
        )
        .values(
            "id",
            "starts_at",
            "price_minor",
            "service_id",
            "service__name",
            "client_id",
            "client_phone",
        )
        .order_by("starts_at")
    )
    main_staff = {}
    for step in AppointmentStep.objects.filter(
        appointment_id__in=[d["id"] for d in done], kind="work", staff__isnull=False
    ).order_by("position"):
        main_staff.setdefault(step.appointment_id, step.staff_id)
    staff_rows = []
    names = {m.pk: m for m in StaffMember.objects.filter(pro=pro)}
    for staff_id, member in names.items():
        mine = [d for d in done if main_staff.get(d["id"]) == staff_id]
        stats = per_staff.get(staff_id, {"open_minutes": 0, "booked_minutes": 0, "occupancy": 0})
        if not mine and not stats["open_minutes"]:
            continue
        staff_rows.append(
            {
                "id": str(staff_id),
                "name": member.name,
                "color": member.color,
                "appointments": len(mine),
                "turnover_minor": sum(d["price_minor"] or 0 for d in mine),
                **stats,
            }
        )
    services: dict = {}
    for d in done:
        row = services.setdefault(
            d["service_id"],
            {
                "id": str(d["service_id"]),
                "name": d["service__name"],
                "appointments": 0,
                "turnover_minor": 0,
            },
        )
        row["appointments"] += 1
        row["turnover_minor"] += d["price_minor"] or 0
    clients = {_client_key(d) for d in done}
    firsts = Appointment.objects.filter(pro=pro, status=A.COMPLETED).filter(
        Q(client_id__in=[k[1] for k in clients if k[0] == "c"])
        | Q(client__isnull=True, client_phone__in=[k[1] for k in clients if k[0] == "p"])
    )
    first_seen = {}
    for row in firsts.values("client_id", "client_phone").annotate(first=Min("starts_at")):
        first_seen[_client_key(row)] = min(
            row["first"], first_seen.get(_client_key(row), row["first"])
        )
    new = sum(1 for k in clients if first_seen.get(k) and first_seen[k] >= since)
    result = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        **money,
        "occupancy": rate,
        "clients": len(clients),
        "new_clients": new,
        "loyal_clients": len(clients) - new,
        "staff": sorted(staff_rows, key=lambda r: -r["turnover_minor"]),
        "services": sorted(services.values(), key=lambda r: -r["turnover_minor"])[:10],
        "series": _series(pro, start, end, done, zone),
    }
    cache.set(key, result, 600)
    return result


def dashboard(pro, start: datetime.date, end: datetime.date, today: datetime.date) -> dict:
    if not selectors.has_feature(pro, Feature.DASHBOARD):
        return {"level": "basic", "basic": basic(pro, today), "current": None, "previous": None}
    current = complete(pro, start, end)
    length = (datetime.date.fromisoformat(current["end"]) - start).days + 1
    before_end = start - datetime.timedelta(days=1)
    previous = complete(pro, before_end - datetime.timedelta(days=length - 1), before_end)
    return {
        "level": "complete",
        "basic": basic(pro, today),
        "current": current,
        "previous": previous,
    }
