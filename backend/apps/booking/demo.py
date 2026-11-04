"""Demo agendas (development only, idempotent): two salons with their team and their
appointments, a salon that accepts each request by hand, a waiting list."""

from __future__ import annotations

import contextlib
import datetime

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.errors import DomainError
from apps.pros.hours import zone_of
from apps.pros.models import ProProfile

from . import selectors
from .models import (
    BookingSettings,
    ManualSlot,
    Place,
    PlacePeriod,
    Resource,
    StaffMember,
    WaitlistEntry,
)
from .services import agenda, appointments, common, waitlist

TEAMS = {
    "institut-prisca": {
        "people": [("Mireille", "#7A3E9D"), ("Sandra", "#1F7A5A"), ("Joëlle", "#2563A8")],
        "resources": [("Cabine de soin", 2)],
        "auto_confirm": True,
    },
    "fatou-braids": {
        "people": [("Aminata", "#7A3E9D"), ("Kadi", "#B54708")],
        "resources": [],
        "auto_confirm": False,
    },
    # Accepts each request by hand: the end-to-end journey books here.
    "bene-coiffure": {"people": [], "resources": [("Bac", 1)], "auto_confirm": False},
}

CLIENTS = {"BJ": ["+2290197000201", "+2290196000202"], "FR": ["+33612340204"]}


def _at(pro, days: int, hour: int) -> datetime.datetime:
    zone = zone_of(pro)
    day = (timezone.now().astimezone(zone) + datetime.timedelta(days=days)).date()
    return datetime.datetime.combine(day, datetime.time(hour), tzinfo=zone)


def _book(pro, service, start, **kwargs) -> bool:
    try:
        with transaction.atomic():
            appointments.book(pro, service.pk, start, **kwargs)
    except DomainError:
        return False
    return True


def _fill(pro: ProProfile, team: dict) -> int:
    selectors.owner_staff(pro)
    # Created here on a new database (the settings only exist once someone books).
    pro._booking_settings = BookingSettings.objects.update_or_create(
        pro=pro, defaults={"auto_confirm": team["auto_confirm"]}
    )[0]
    if StaffMember.objects.filter(pro=pro, is_owner=False).exists() or pro.appointments.exists():
        return 0
    for name, color in team["people"]:
        agenda.save_staff(pro, name=name, color=color)
    for name, quantity in team["resources"]:
        Resource.objects.get_or_create(pro=pro, name=name, defaults={"quantity": quantity})
    services = list(pro.services.filter(is_active=True).order_by("position", "name"))
    if not services:
        return 0
    country = pro.country.code if pro.country_id else "BJ"
    clients = list(User.objects.filter(phone__in=CLIENTS.get(country, [])))
    count = 0
    for index, client in enumerate(clients):
        service = services[index % len(services)]
        count += _book(pro, service, _at(pro, 1, 10 + 3 * index), user=client)
    # A client who called the salon, booked by the pro herself.
    count += _book(
        pro,
        services[0],
        _at(pro, 2, 11),
        guest_name="Bernadette",
        guest_phone="+2290197000301" if country == "BJ" else "+33612340301",
        source="phone",
        by_pro=pro.user,
    )
    if clients:
        with contextlib.suppress(DomainError):
            waitlist.join(pro, services[0].pk, _at(pro, 1, 9).date(), user=clients[-1])
    return count


def _places_and_opened_times() -> None:
    """Prisca also works in Akpakpa on Saturdays; Béné opens an evening herself."""
    prisca = ProProfile.objects.filter(slug="institut-prisca").first()
    if prisca is not None and not prisca.places.exists():
        place = Place.objects.create(
            pro=prisca, name="Annexe Akpakpa", city="Cotonou", district="Akpakpa"
        )
        PlacePeriod.objects.create(
            place=place, weekday=5, starts_at=datetime.time(9), ends_at=datetime.time(14)
        )
    bene = ProProfile.objects.filter(slug="bene-coiffure").first()
    if bene is not None and not bene.manual_slots.exists():
        start = _at(bene, 3, 19)
        ManualSlot.objects.create(
            pro=bene,
            starts_at=start,
            ends_at=start + datetime.timedelta(hours=2),
            note="Soirée spéciale",
        )
        common.changed(bene)


def seed_booking() -> dict:
    counts = {"agendas": 0, "appointments": 0, "waiting": 0}
    pros = ProProfile.objects.filter(slug__in=TEAMS, status=ProProfile.Status.PUBLISHED)
    for pro in pros.select_related("user", "country"):
        counts["appointments"] += _fill(pro, TEAMS[pro.slug])
        counts["agendas"] += 1
    counts["waiting"] = WaitlistEntry.objects.filter(pro__slug__in=TEAMS).count()
    _places_and_opened_times()
    return counts
