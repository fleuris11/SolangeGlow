"""What a pro decides about her time: times she opens, several places, visits at home,
margins between clients, a pause, and appointments she adds whenever she wants."""

import datetime

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.booking import availability, errors
from apps.booking.models import (
    Appointment,
    BookingSettings,
    ManualSlot,
    Place,
    PlacePeriod,
    TimeOff,
)
from apps.booking.services import agenda, appointments
from apps.messaging.tests.factories import adult
from apps.pros.models import Closure

from .factories import MONDAY, at, person, salon, service

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def starts(slots) -> set[datetime.datetime]:
    return {slot.start for slot in slots}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def setting(pro, **values):
    agenda.update_settings(pro, **values)
    pro.refresh_from_db()
    pro.__dict__.pop("_booking_settings", None)


def test_she_opens_a_time_outside_her_hours():
    pro = salon()
    svc = service(pro, ("work", 60))
    assert at(20) not in starts(availability.day_slots(pro, svc, MONDAY))
    agenda.open_slots(pro, starts_at=at(19), ends_at=at(21))
    assert at(20) in starts(availability.day_slots(pro, svc, MONDAY))
    booked = appointments.book(pro, svc.pk, at(20), user=adult("Awa"))
    assert booked.starts_at == at(20)


def test_an_opened_time_goes_over_a_closure_but_not_over_what_she_blocked():
    pro = salon()
    svc = service(pro, ("work", 60))
    Closure.objects.create(pro=pro, starts_on=MONDAY, ends_on=MONDAY)
    agenda.common.changed(pro)
    assert availability.day_slots(pro, svc, MONDAY) == []
    agenda.open_slots(pro, starts_at=at(10), ends_at=at(12))
    assert at(10) in starts(availability.day_slots(pro, svc, MONDAY))
    TimeOff.objects.create(pro=pro, starts_at=at(10), ends_at=at(12))
    agenda.common.changed(pro)
    assert availability.day_slots(pro, svc, MONDAY) == []


def test_only_the_times_she_opens():
    pro = salon()
    svc = service(pro, ("work", 60))
    setting(pro, slot_mode="manual")
    assert availability.day_slots(pro, svc, MONDAY) == []
    slots = agenda.open_slots(pro, starts_at=at(10), ends_at=at(11), repeat_weeks=2)
    assert len(slots) == 3
    assert slots[2].starts_at == at(10) + datetime.timedelta(weeks=2)
    assert starts(availability.day_slots(pro, svc, MONDAY)) == {at(10)}
    agenda.close_slot(pro, slots[0].pk)
    assert availability.day_slots(pro, svc, MONDAY) == []
    with pytest.raises(errors.SlotNotFound):
        agenda.close_slot(pro, slots[0].pk)


def test_an_opened_time_can_be_kept_for_some_services():
    pro = salon()
    braids = service(pro, ("work", 60), name="Tresses")
    nails = service(pro, ("work", 60), name="Ongles")
    setting(pro, slot_mode="manual")
    agenda.open_slots(pro, starts_at=at(10), ends_at=at(11), service_ids=[braids.pk])
    assert availability.day_slots(pro, braids, MONDAY)
    assert availability.day_slots(pro, nails, MONDAY) == []


def test_an_opened_time_must_make_sense():
    pro = salon()
    with pytest.raises(errors.InvalidTimeRange):
        agenda.open_slots(pro, starts_at=at(11), ends_at=at(10))
    long_ago = at(10) - datetime.timedelta(days=3650)
    with pytest.raises(errors.SlotInThePast):
        agenda.open_slots(pro, starts_at=long_ago, ends_at=long_ago + datetime.timedelta(hours=1))
    with pytest.raises(errors.PlaceNotFound):
        agenda.open_slots(
            pro,
            starts_at=at(10),
            ends_at=at(11),
            place_id="00000000-0000-0000-0000-000000000000",
        )
    with pytest.raises(errors.StaffNotFound):
        agenda.open_slots(
            pro,
            starts_at=at(10),
            ends_at=at(11),
            staff_id="00000000-0000-0000-0000-000000000000",
        )


def test_time_kept_between_two_clients():
    pro = salon()
    svc = service(pro, ("work", 60))
    appointments.book(pro, svc.pk, at(10), user=adult("Awa"))
    assert at(11) in starts(availability.day_slots(pro, svc, MONDAY))
    setting(pro, buffer_minutes=30)
    found = starts(availability.day_slots(pro, svc, MONDAY))
    assert at(11) not in found and at(11, 30) in found
    assert at(9) not in found and at(8, 30) not in found


def test_she_works_in_another_place_and_is_never_in_two_places():
    pro = salon()
    svc = service(pro, ("work", 60))
    calavi = agenda.save_place(pro, name="Calavi", city="Calavi", latitude=6.4, longitude=2.3)
    assert calavi.location is not None
    agenda.set_place_hours(
        pro,
        calavi.pk,
        [
            {
                "weekday": MONDAY.weekday(),
                "starts_at": datetime.time(9),
                "ends_at": datetime.time(18),
            }
        ],
    )
    booked = appointments.book(pro, svc.pk, at(10), user=adult("Awa"), place_id=calavi.pk)
    assert booked.place == calavi
    assert at(10) not in starts(availability.day_slots(pro, svc, MONDAY))
    assert at(11) in starts(availability.day_slots(pro, svc, MONDAY))
    setting(pro, travel_minutes=45)
    main = starts(availability.day_slots(pro, svc, MONDAY))
    assert at(11) not in main and at(12) in main
    # At the same address she needs no time to travel.
    same = starts(availability.day_slots(pro, svc, MONDAY, place_id=calavi.pk))
    assert at(11) in same
    agenda.remove_place(pro, calavi.pk)
    with pytest.raises(errors.PlaceNotFound):
        appointments.book(pro, svc.pk, at(15), user=adult("Inès"), place_id=calavi.pk)
    booked.refresh_from_db()
    assert booked.place == calavi


def test_a_place_has_its_own_hours():
    pro = salon()
    svc = service(pro, ("work", 60))
    place = Place.objects.create(pro=pro, name="Calavi")
    assert availability.day_slots(pro, svc, MONDAY, place_id=place.pk) == []
    PlacePeriod.objects.create(
        place=place,
        weekday=MONDAY.weekday(),
        starts_at=datetime.time(9),
        ends_at=datetime.time(10),
    )
    agenda.common.changed(pro)
    assert starts(availability.day_slots(pro, svc, MONDAY, place_id=place.pk)) == {at(9)}


def test_a_visit_at_home_adds_the_fee_and_needs_an_address():
    pro = salon()
    svc = service(pro, ("work", 60), price=20_000, available_at_home=True)
    with pytest.raises(errors.NoHomeVisits):
        appointments.book(
            pro, svc.pk, at(10), user=adult("Awa"), at_home=True, client_address="Rue 12"
        )
    pro.travels_to_clients = True
    pro.travel_fee_minor = 2_000
    pro.save()
    with pytest.raises(errors.AddressNeeded):
        appointments.book(pro, svc.pk, at(10), user=adult("Awa"), at_home=True)
    booked = appointments.book(
        pro, svc.pk, at(10), user=adult("Inès"), at_home=True, client_address="Rue 12"
    )
    assert booked.at_home and booked.client_address == "Rue 12"
    assert booked.price_minor == 22_000 and booked.travel_fee_minor == 2_000


def test_a_pause_stops_online_booking_but_not_the_agenda():
    pro = salon()
    svc = service(pro, ("work", 60))
    setting(pro, online_paused=True)
    with pytest.raises(errors.BookingPaused):
        appointments.book(pro, svc.pk, at(10), user=adult("Awa"))
    booked = appointments.book(
        pro, svc.pk, at(10), guest_name="Awa", guest_phone="+2290197000001", by_pro=pro.user
    )
    assert booked.status == Appointment.Status.CONFIRMED
    url = reverse("v1:booking-slots", args=[pro.slug])
    days = APIClient().get(url, {"service": str(svc.pk), "day": MONDAY.isoformat()}).json()["days"]
    assert all(day["slots"] == [] for day in days)
    assert APIClient().get(reverse("v1:booking-page", args=[pro.slug])).json()["online_paused"]


def test_she_adds_or_moves_an_appointment_outside_her_hours():
    pro = salon()
    svc = service(pro, ("work", 60))
    details = {"guest_name": "Awa", "guest_phone": "+2290197000001", "by_pro": pro.user}
    with pytest.raises(errors.SlotTaken):
        appointments.book(pro, svc.pk, at(21), **details)
    booked = appointments.book(pro, svc.pk, at(21), outside_hours=True, **details)
    assert booked.starts_at == at(21)
    # She still cannot be with two clients at once.
    with pytest.raises(errors.SlotTaken):
        appointments.book(pro, svc.pk, at(21), outside_hours=True, **details)
    # A client cannot use it.
    with pytest.raises(errors.SlotTaken):
        appointments.book(pro, svc.pk, at(22), user=adult("Inès"), outside_hours=True)
    with pytest.raises(errors.SlotTaken):
        appointments.move(booked, actor=pro.user, start=at(23))
    appointments.move(booked, actor=pro.user, start=at(23), outside_hours=True)
    booked.refresh_from_db()
    assert booked.starts_at == at(23)


def test_opened_times_and_places_through_the_api():
    pro = salon()
    svc = service(pro, ("work", 60))
    owner = signed_in(pro.user)
    assert BookingSettings.objects.get_or_create(pro=pro)[0].slot_mode == "hours"
    changed = owner.patch(
        reverse("v1:agenda-settings"),
        {"slot_mode": "manual", "buffer_minutes": 15, "travel_minutes": 30, "online_paused": True},
        format="json",
        **H,
    ).json()
    assert changed["slot_mode"] == "manual" and changed["online_paused"] is True
    owner.patch(reverse("v1:agenda-settings"), {"online_paused": False}, format="json", **H)

    place = owner.post(
        reverse("v1:agenda-places"),
        {"name": "Calavi", "city": "Calavi", "latitude": 6.4, "longitude": 2.3},
        format="json",
        **H,
    ).json()
    assert place["latitude"] == 6.4
    hours = owner.put(
        reverse("v1:agenda-place-hours", args=[place["id"]]),
        {"hours": [{"weekday": 0, "starts_at": "09:00", "ends_at": "12:00"}]},
        format="json",
        **H,
    ).json()
    assert hours["hours"][0]["ends_at"] == "12:00"
    wrong = owner.put(
        reverse("v1:agenda-place-hours", args=[place["id"]]),
        {"hours": [{"weekday": 0, "starts_at": "12:00", "ends_at": "09:00"}]},
        format="json",
        **H,
    )
    assert wrong.status_code == 400
    renamed = owner.patch(
        reverse("v1:agenda-place", args=[place["id"]]), {"name": "Godomey"}, format="json", **H
    ).json()
    assert renamed["name"] == "Godomey"
    assert [row["name"] for row in owner.get(reverse("v1:agenda-places")).json()] == ["Godomey"]
    page = APIClient().get(reverse("v1:booking-page", args=[pro.slug])).json()
    assert [row["name"] for row in page["places"]] == ["Godomey"]

    opened = owner.post(
        reverse("v1:agenda-slots"),
        {
            "starts_at": at(10).isoformat(),
            "ends_at": at(11).isoformat(),
            "place_id": place["id"],
            "service_ids": [str(svc.pk)],
            "repeat_weeks": 1,
            "note": "Samedi spécial",
        },
        format="json",
        **H,
    )
    assert opened.status_code == 201 and len(opened.json()) == 2
    listed = owner.get(reverse("v1:agenda-slots"), {"day": MONDAY.isoformat()}).json()
    assert listed[0]["place_name"] == "Godomey" and listed[0]["service_ids"] == [str(svc.pk)]
    slots = APIClient().get(
        reverse("v1:booking-slots", args=[pro.slug]),
        {"service": str(svc.pk), "day": MONDAY.isoformat(), "place": place["id"]},
    )
    assert slots.json()["days"][0]["slots"]
    booked = APIClient().post(
        reverse("v1:booking-page", args=[pro.slug]),
        {
            "service_id": str(svc.pk),
            "start": at(10).isoformat(),
            "guest_name": "Awa",
            "guest_phone": "+2290197000001",
            "place_id": place["id"],
        },
        format="json",
        **H,
    )
    assert booked.status_code == 201
    assert booked.json()["appointment"]["place"]["name"] == "Godomey"

    deleted = owner.delete(reverse("v1:agenda-slot", args=[listed[1]["id"]]), **H)
    assert deleted.status_code == 204
    assert ManualSlot.objects.filter(pro=pro).count() == 1
    assert owner.delete(reverse("v1:agenda-place", args=[place["id"]]), **H).status_code == 204
    assert owner.get(reverse("v1:agenda-places")).json() == []


def test_a_collaborator_and_a_stranger_cannot_change_them():
    pro = salon()
    helper = person(pro, name="Fifamè")
    helper.user = adult("Fifamè")
    helper.save()
    for user in (helper.user, adult("Inès")):
        answer = signed_in(user).post(
            reverse("v1:agenda-places"), {"name": "Calavi"}, format="json", **H
        )
        assert answer.status_code in (403, 404)
        assert signed_in(user).get(reverse("v1:agenda-slots")).status_code in (403, 404)
    assert not Place.objects.exists()


def test_the_pro_books_a_visit_from_her_agenda_outside_her_hours():
    pro = salon()
    pro.travels_to_clients = True
    pro.save()
    svc = service(pro, ("work", 60), available_at_home=True)
    answer = signed_in(pro.user).post(
        reverse("v1:agenda-new"),
        {
            "service_id": str(svc.pk),
            "start": at(21).isoformat(),
            "client_name": "Awa",
            "client_phone": "+2290197000001",
            "at_home": True,
            "client_address": "Rue 12",
            "outside_hours": True,
        },
        format="json",
        **H,
    )
    assert answer.status_code == 201
    assert answer.json()["appointment"]["client_address"] == "Rue 12"


def test_a_pro_gets_an_email_with_the_way_to_the_appointment():
    from apps.notifications.models import Notification, NotificationTemplate

    assert NotificationTemplate.objects.get(event_key="booking.new", channel="email").is_active
    assert NotificationTemplate.objects.get(event_key="booking.request", channel="email").is_active
    pro = salon()
    svc = service(pro, ("work", 60))
    booked = appointments.book(pro, svc.pk, at(10), user=adult("Awa"))
    sent = Notification.objects.filter(user=pro.user, event_key="booking.new").first()
    assert sent is not None
    assert f"rdv={booked.pk}" in sent.link
