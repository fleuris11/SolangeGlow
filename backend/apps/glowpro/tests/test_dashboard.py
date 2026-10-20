"""The dashboard: basic for free, complete for Premium (with the period before)."""

import datetime

import pytest
from django.utils import timezone

from apps.booking.services import appointments
from apps.booking.tests.factories import MONDAY, at, person, salon, service
from apps.glowpro import stats
from apps.messaging.tests.factories import adult
from apps.salon.services import onsite

from .factories import premium

pytestmark = pytest.mark.django_db


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = at(8, day=datetime.date(2030, 1, 5))

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def test_basic_then_complete(clock):
    pro = salon(hours=((9, 0), (13, 0)))  # 4 hours a day
    carine = person(pro, "Carine")
    svc = service(pro, ("work", 60), name="Brushing", price=10_000)
    awa, ines = adult("Awa"), adult("Inès")
    first = appointments.book(pro, svc.pk, at(9), user=awa)
    second = appointments.book(pro, svc.pk, at(10), user=ines, staff_id=carine.pk)
    appointments.book(pro, svc.pk, at(9, day=MONDAY + datetime.timedelta(days=1)), user=awa)
    clock.set(at(12))
    for booked in (first, second):
        appointments.complete(booked, actor=pro.user)
    onsite.record_payment(
        pro, amount_minor=10_000, method="cash", actor=pro.user, appointment=first
    )

    free = stats.dashboard(pro, MONDAY, MONDAY, MONDAY)
    assert free["level"] == "basic" and free["current"] is None
    assert free["basic"]["turnover_minor"] == 20_000 and free["basic"]["appointments"] == 2

    premium(pro)
    pro.__dict__.pop("_glowpro_subscription", None)
    found = stats.dashboard(pro, MONDAY, MONDAY + datetime.timedelta(days=1), MONDAY)
    current = found["current"]
    assert found["level"] == "complete"
    assert current["turnover_minor"] == 20_000 and current["average_minor"] == 10_000
    assert current["collected_on_site_minor"] == 10_000
    # Two people x 4 hours x 2 days = 960 min open; 3 hours booked (two done, one coming).
    assert current["occupancy"] == round(100 * 180 / 960)
    assert current["new_clients"] == 2 and current["loyal_clients"] == 0
    by_name = {row["name"]: row for row in current["staff"]}
    assert by_name["Carine"]["appointments"] == 1 and by_name["Carine"]["turnover_minor"] == 10_000
    assert current["services"][0]["name"] == "Brushing"
    assert [day["turnover_minor"] for day in current["series"]] == [20_000, 0]
    assert found["previous"]["turnover_minor"] == 0
