"""The booking API: a guest books and manages with her link, a client pays a deposit,
the pro and a collaborator work in the agenda."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.booking.models import Appointment, BookingSettings, ClientRecord, StaffMember
from apps.booking.services import agenda
from apps.messaging.tests.factories import adult

from .factories import MONDAY, at, salon, service

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}
A = Appointment.Status
GUEST_PHONE = "+2290197000001"


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def iso(moment: datetime.datetime) -> str:
    return moment.isoformat()


def test_the_booking_page_and_its_slots():
    pro = salon()
    svc = service(
        pro, ("work", 30), ("wait", 30), ("work", 30), deposit_kind="amount", deposit_value=5_000
    )
    page = APIClient().get(reverse("v1:booking-page", args=[pro.slug])).json()
    assert page["pro"]["slug"] == pro.slug and page["accepts_guests"] is True
    assert page["services"][0]["id"] == str(svc.pk)
    assert (
        page["services"][0]["work_minutes"] == 60 and page["services"][0]["deposit_minor"] == 5_000
    )
    assert [m["name"] for m in page["staff"]] == [pro.display_name]
    slots = (
        APIClient()
        .get(
            reverse("v1:booking-slots", args=[pro.slug]),
            {"service": str(svc.pk), "day": MONDAY.isoformat(), "days": 2},
        )
        .json()
    )
    assert [d["day"] for d in slots["days"]] == ["2030-01-07", "2030-01-08"]
    assert slots["days"][0]["slots"][0]["start"] == "2030-01-07T08:00:00+00:00"  # 9:00 local
    assert slots["next_day"] == "2030-01-09"
    missing = APIClient().get(reverse("v1:booking-page", args=["nobody"]))
    assert missing.status_code == 404 and missing.json()["code"] == "booking_pro_not_found"


def test_a_guest_books_then_cancels_with_her_link():
    pro = salon()
    svc = service(pro, ("work", 60))
    answer = APIClient().post(
        reverse("v1:booking-page", args=[pro.slug]),
        {
            "service_id": str(svc.pk),
            "start": iso(at(10)),
            "guest_name": "Inès",
            "guest_phone": GUEST_PHONE,
        },
        format="json",
    )
    assert answer.status_code == 201
    booked = answer.json()
    assert booked["appointment"]["status"] == "confirmed" and booked["checkout_url"] is None
    token = booked["manage_url"].split("/")[-1]
    seen = APIClient().get(reverse("v1:guest-appointment", args=[token])).json()
    assert seen["reference"] == booked["appointment"]["reference"]
    assert seen["client_phone"] == ""  # never sent back
    cancelled = (
        APIClient()
        .post(reverse("v1:guest-appointment-cancel", args=[token]), {}, format="json")
        .json()
    )
    assert cancelled["status"] == "cancelled"
    wrong = APIClient().get(reverse("v1:guest-appointment", args=["nope"]))
    assert wrong.status_code == 404


def test_a_client_books_with_a_deposit_and_gets_the_payment_page():
    pro = salon()
    svc = service(pro, ("work", 60), deposit_kind="percent", deposit_value=30)
    client = adult("Awa")
    booked = (
        signed_in(client)
        .post(
            reverse("v1:booking-page", args=[pro.slug]),
            {"service_id": str(svc.pk), "start": iso(at(10))},
            format="json",
            **H,
        )
        .json()
    )
    assert booked["appointment"]["status"] == "awaiting_deposit"
    assert booked["checkout_url"] and booked["manage_url"] is None
    mine = signed_in(client).get(reverse("v1:my-appointments")).json()
    assert [a["id"] for a in mine["upcoming"]] == [booked["appointment"]["id"]]
    again = (
        signed_in(client)
        .post(reverse("v1:my-appointment-pay", args=[booked["appointment"]["id"]]), {}, **H)
        .json()
    )
    assert again["checkout_url"] == booked["checkout_url"]
    stranger = signed_in(adult("Inès")).get(
        reverse("v1:my-appointment", args=[booked["appointment"]["id"]])
    )
    assert stranger.status_code == 404


def test_a_taken_slot_answers_409():
    pro = salon()
    svc = service(pro, ("work", 60))
    body = {"service_id": str(svc.pk), "start": iso(at(10))}
    assert (
        signed_in(adult("Awa"))
        .post(reverse("v1:booking-page", args=[pro.slug]), body, format="json", **H)
        .status_code
        == 201
    )
    taken = signed_in(adult("Inès")).post(
        reverse("v1:booking-page", args=[pro.slug]), body, format="json", **H
    )
    assert taken.status_code == 409 and taken.json()["code"] == "slot_taken"


def test_the_agenda_opens_on_today_in_the_pros_zone(monkeypatch):
    pro = salon()
    svc = service(pro, ("work", 60))
    booked = (
        signed_in(adult("Awa"))
        .post(
            reverse("v1:booking-page", args=[pro.slug]),
            {"service_id": str(svc.pk), "start": iso(at(10))},
            format="json",
            **H,
        )
        .json()["appointment"]
    )
    # Sunday 23:30 UTC is already Monday 0:30 in Cotonou: the agenda shows Monday.
    late = datetime.datetime(2030, 1, 6, 23, 30, tzinfo=datetime.UTC)
    monkeypatch.setattr(timezone, "now", lambda: late)
    day = signed_in(pro.user).get(reverse("v1:agenda"), {"days": 1}).json()
    assert [a["id"] for a in day["appointments"]] == [booked["id"]]


def test_the_pro_works_in_her_agenda():
    pro = salon()
    agenda.update_settings(pro, auto_confirm=False)
    svc = service(pro, ("work", 60))
    owner = signed_in(pro.user)
    client = adult("Awa")
    asked = (
        signed_in(client)
        .post(
            reverse("v1:booking-page", args=[pro.slug]),
            {"service_id": str(svc.pk), "start": iso(at(10)), "note": "Cheveux fins"},
            format="json",
            **H,
        )
        .json()["appointment"]
    )
    day = owner.get(reverse("v1:agenda"), {"start": MONDAY.isoformat(), "days": 1}).json()
    assert day["can_manage"] and day["pending_count"] == 1
    assert [a["id"] for a in day["pending"]] == [asked["id"]]
    assert [a["id"] for a in day["appointments"]] == [asked["id"]]
    assert day["appointments"][0]["note"] == "Cheveux fins"
    confirmed = owner.post(reverse("v1:agenda-confirm", args=[asked["id"]]), {}, **H).json()
    assert (
        confirmed["appointment"]["status"] == "confirmed" and confirmed["record"]["name"] == "Awa"
    )
    moved = owner.post(
        reverse("v1:agenda-move", args=[asked["id"]]), {"start": iso(at(14))}, format="json", **H
    ).json()
    assert moved["appointment"]["starts_at"].startswith("2030-01-07T13:00")  # 14:00 in Cotonou
    quick = owner.post(
        reverse("v1:agenda-new"),
        {
            "service_id": str(svc.pk),
            "start": iso(at(9)),
            "client_name": "Mamie Rose",
            "client_phone": "+2290197000077",
        },
        format="json",
        **H,
    )
    assert quick.status_code == 201
    assert quick.json()["appointment"]["source"] == "phone"
    assert quick.json()["appointment"]["client_phone"] == "+2290197000077"
    blocked = owner.post(
        reverse("v1:agenda-time-off"),
        {"starts_at": iso(at(16)), "ends_at": iso(at(18)), "note": "Formation"},
        format="json",
        **H,
    )
    assert blocked.status_code == 201 and blocked.json()["kind"] == "block"
    taken = owner.post(
        reverse("v1:agenda-move", args=[asked["id"]]), {"start": iso(at(16))}, format="json", **H
    )
    assert taken.status_code == 409


def test_a_collaborator_sees_only_her_appointments():
    pro = salon()
    svc = service(pro, ("work", 60))
    carine = adult("Carine", phone="+2290197000009")
    owner = signed_in(pro.user)
    staff = owner.post(
        reverse("v1:agenda-staff"),
        {"name": "Carine", "color": "#7A3E9D", "phone": "+2290197000009"},
        format="json",
        **H,
    ).json()
    assert staff["has_account"] is True
    hers = (
        signed_in(adult("Awa"))
        .post(
            reverse("v1:booking-page", args=[pro.slug]),
            {"service_id": str(svc.pk), "start": iso(at(10)), "staff_id": staff["id"]},
            format="json",
            **H,
        )
        .json()["appointment"]
    )
    signed_in(adult("Inès")).post(
        reverse("v1:booking-page", args=[pro.slug]),
        {"service_id": str(svc.pk), "start": iso(at(10))},
        format="json",
        **H,
    )
    mine = signed_in(carine)
    seen = mine.get(reverse("v1:agenda"), {"start": MONDAY.isoformat()}).json()
    assert seen["can_manage"] is False and [a["id"] for a in seen["appointments"]] == [hers["id"]]
    assert [m["name"] for m in seen["staff"]] == ["Carine"]
    other = Appointment.objects.exclude(pk=hers["id"]).get()
    assert mine.get(reverse("v1:agenda-appointment", args=[other.pk])).status_code == 404
    assert mine.get(reverse("v1:agenda-settings")).status_code == 403
    assert mine.get(reverse("v1:agenda-staff")).status_code == 403
    assert (
        signed_in(adult("Sika"))
        .get(reverse("v1:agenda"), {"start": MONDAY.isoformat()})
        .status_code
        == 404
    )


def test_people_hours_settings_and_resources():
    pro = salon()
    owner = signed_in(pro.user)
    staff = owner.post(
        reverse("v1:agenda-staff"), {"name": "Sika", "own_hours": True}, format="json", **H
    ).json()
    hours = owner.put(
        reverse("v1:agenda-staff-hours", args=[staff["id"]]),
        {
            "periods": [{"weekday": 0, "starts_at": "10:00", "ends_at": "16:00"}],
            "breaks": [{"weekday": 0, "starts_at": "12:00", "ends_at": "12:30"}],
        },
        format="json",
        **H,
    ).json()
    assert hours["periods"] == [{"weekday": 0, "starts_at": "10:00", "ends_at": "16:00"}]
    renamed = owner.patch(
        reverse("v1:agenda-staff-item", args=[staff["id"]]), {"daily_limit": 4}, format="json", **H
    ).json()
    assert renamed["name"] == "Sika" and renamed["daily_limit"] == 4
    changed = owner.patch(
        reverse("v1:agenda-settings"),
        {"auto_confirm": False, "free_cancel_hours": 48, "slot_step_minutes": 30},
        format="json",
        **H,
    ).json()
    assert changed["auto_confirm"] is False and changed["free_cancel_hours"] == 48
    assert changed["booking_url"].endswith(f"/{pro.slug}/rdv")
    assert changed["defaults"]["free_cancel_hours"] == 24
    bac = owner.post(
        reverse("v1:agenda-resources"), {"name": "Bac", "quantity": 2}, format="json", **H
    ).json()
    assert bac["quantity"] == 2
    assert owner.get(reverse("v1:agenda-settings")).json()["resources"][0]["name"] == "Bac"
    offer = owner.put(
        reverse("v1:agenda-last-minute"),
        {"percent_off": 15, "window_hours": 12, "is_active": True},
        format="json",
        **H,
    ).json()
    assert offer == {"percent_off": 15, "window_hours": 12, "is_active": True}
    qr = owner.get(reverse("v1:agenda-qr"))
    assert qr.status_code == 200 and qr["Content-Type"] == "image/png"


def test_client_files_and_ical():
    pro = salon()
    svc = service(pro, ("work", 60))
    soon = timezone.localdate() + datetime.timedelta(days=2)
    signed_in(adult("Awa")).post(
        reverse("v1:booking-page", args=[pro.slug]),
        {"service_id": str(svc.pk), "start": iso(at(10, day=soon))},
        format="json",
        **H,
    )
    owner = signed_in(pro.user)
    files = owner.get(reverse("v1:agenda-clients"), {"q": "aw"}).json()
    assert [f["name"] for f in files] == ["Awa"]
    record = owner.patch(
        reverse("v1:agenda-client", args=[files[0]["id"]]),
        {"notes": "Allergie à l'ammoniaque"},
        format="json",
        **H,
    ).json()
    assert record["notes"] == "Allergie à l'ammoniaque" and len(record["history"]) == 1
    token = BookingSettings.objects.get(pro=pro).ical_token
    calendar = APIClient().get(reverse("v1:agenda-ical", args=[token]))
    assert calendar.status_code == 200 and b"BEGIN:VEVENT" in calendar.content
    assert APIClient().get(reverse("v1:agenda-ical", args=["wrong"])).status_code == 404
    assert ClientRecord.objects.count() == 1


def test_waiting_list_and_group_through_the_api():
    pro = salon()
    svc = service(pro, ("work", 60))
    joined = APIClient().post(
        reverse("v1:booking-waitlist-join", args=[pro.slug]),
        {
            "service_id": str(svc.pk),
            "day": MONDAY.isoformat(),
            "guest_name": "Inès",
            "guest_phone": GUEST_PHONE,
        },
        format="json",
    )
    assert joined.status_code == 201 and joined.json()["status"] == "waiting"
    StaffMember.objects.create(pro=pro, name="Carine")
    bride = signed_in(adult("Mireille"))
    group = bride.post(
        reverse("v1:booking-group-new", args=[pro.slug]),
        {"service_id": str(svc.pk), "start": iso(at(9)), "size": 2, "title": "Mariage"},
        format="json",
        **H,
    ).json()
    assert group["status"] == "confirmed" and len(group["places"]) == 2
    token = group["share_url"].split("/")[-1]
    shown = APIClient().get(reverse("v1:booking-group", args=[token])).json()
    assert shown["title"] == "Mariage" and shown["is_organizer"] is False
