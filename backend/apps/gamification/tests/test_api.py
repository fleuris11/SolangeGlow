"""The screens of the games through the API: « My points », the home widget (also for
visitors), quiz, wheel, « Help me choose », challenge, rewards, referral, routine,
calendar and rankings; guests cannot play."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.gamification.models import Challenge, GlowProfile, QuizDay, QuizQuestion, WheelPrize
from apps.gamification.services import challenges, points
from apps.messaging.tests.factories import adult
from apps.social.tests.factories import asset

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_guests_see_the_home_widget_but_cannot_play():
    guest = APIClient()
    today = guest.get("/api/v1/glow/today")
    assert today.status_code == 200
    assert today.json()["signed_in"] is False
    assert today.json()["summary"] is None
    for url in ("/api/v1/glow/me", "/api/v1/glow/wheel", "/api/v1/glow/quiz"):
        assert guest.get(url).status_code in (401, 403)
    assert guest.post("/api/v1/glow/check-in", **H).status_code in (401, 403)


def test_my_points_check_in_and_history():
    awa = adult()
    client = signed_in(awa)
    first = client.post("/api/v1/glow/check-in", **H).json()
    assert (first["streak"], first["gained"], first["balance"]) == (1, 5, 5)
    me = client.get("/api/v1/glow/me").json()
    assert me["balance"] == 5
    assert me["level"] == "glow"
    assert me["streak"]["today_done"] is True
    assert me["referral"]["path"].startswith("/invite/")
    assert {row["action"] for row in me["scale"]} >= {"checkin", "review", "quiz"}
    history = client.get("/api/v1/glow/history").json()
    assert [row["action"] for row in history] == ["checkin"]
    widget = client.get("/api/v1/glow/today").json()
    assert widget["summary"]["balance"] == 5
    assert widget["wheel"]["can_spin"] is True


def test_quiz_of_the_day_answers_shown_after_answering():
    awa = adult()
    day = QuizDay.objects.create(date=timezone.localdate(), status="approved")
    question = QuizQuestion.objects.create(
        quiz=day, text="Le karité ?", choice_1="Nourrit", choice_2="Sèche", answer=1
    )
    client = signed_in(awa)
    found = client.get("/api/v1/glow/quiz").json()["quiz"]
    assert found["questions"][0]["answer"] is None  # never sent before answering
    answer = client.post(
        f"/api/v1/glow/quiz/{question.pk}/answer", {"choice": 1}, format="json", **H
    ).json()
    assert answer["correct"] is True
    again = client.get("/api/v1/glow/quiz").json()["quiz"]
    assert again["questions"][0]["answer"] == 1
    assert again["score"] == 1


def test_wheel_spin_and_its_chances():
    WheelPrize.objects.all().delete()
    WheelPrize.objects.create(label="10 points", kind="points", points=10, weight=1)
    client = signed_in(adult())
    shown = client.get("/api/v1/glow/wheel").json()
    assert shown["prizes"][0]["chance"] == "100.0"
    spin = client.post("/api/v1/glow/wheel/spin", **H).json()
    assert (spin["label"], spin["points"]) == ("10 points", 10)
    again = client.post("/api/v1/glow/wheel/spin", **H)
    assert again.status_code == 400
    assert again.json()["code"] == "wheel_already_spun"


def test_help_me_choose_create_vote_and_result():
    awa, fifame = adult(), adult("Fifamè")
    a, b = asset(awa, purpose="poll_photo"), asset(awa, purpose="poll_photo")
    created = signed_in(awa).post(
        "/api/v1/glow/polls",
        {"caption": "Rouge ou wax ?", "photo_a": a.pk, "photo_b": b.pk, "hours": 24},
        format="json",
        **H,
    )
    assert created.status_code == 201
    poll_id = created.json()["id"]
    voter = signed_in(fifame)
    listed = voter.get("/api/v1/glow/polls").json()
    assert listed["durations"] == [1, 6, 24, 72]
    assert listed["results"][0]["result"] is None  # hidden before voting
    voted = voter.post(f"/api/v1/glow/polls/{poll_id}/vote", {"choice": "b"}, format="json", **H)
    assert voted.json()["result"] == {"total": 1, "a": 0, "b": 100}
    mine = signed_in(awa).get("/api/v1/glow/polls?scope=mine").json()["results"]
    assert mine[0]["mine"] is True
    assert signed_in(awa).delete(f"/api/v1/glow/polls/{poll_id}", **H).status_code == 204


def test_challenge_enter_and_vote():
    monday = challenges.monday_of(timezone.localdate())
    Challenge.objects.create(
        theme="Look pagne",
        starts_on=monday,
        ends_on=monday + datetime.timedelta(days=6),
        status="approved",
    )
    awa, fifame = adult(), adult("Fifamè")
    photo = asset(awa, purpose="challenge_photo")
    entered = signed_in(awa).post(
        "/api/v1/glow/challenge/entries", {"photo_id": photo.pk}, format="json", **H
    )
    assert entered.status_code == 201
    entry = entered.json()["current"]["entries"][0]
    voted = signed_in(fifame).post(f"/api/v1/glow/challenge/entries/{entry['id']}/vote", **H)
    assert voted.json()["current"]["entries"][0]["votes"] == 1
    public = APIClient().get("/api/v1/glow/challenge").json()
    assert public["current"]["theme"] == "Look pagne"


def test_rewards_redeem_and_vouchers():
    awa = adult()
    points.adjust(awa, 1000, note="test", actor=None)
    client = signed_in(awa)
    catalogue = client.get("/api/v1/glow/rewards").json()
    cheap = next(r for r in catalogue if r["cost_points"] == 500)
    assert cheap["affordable"] is True
    done = client.post(f"/api/v1/glow/rewards/{cheap['id']}/redeem", **H).json()
    assert done["balance"] == 500
    assert done["voucher"]["code"].startswith("GLOW-")
    assert client.get("/api/v1/glow/vouchers").json()[0]["code"] == done["voucher"]["code"]


def test_invite_link_and_referral():
    awa = adult()
    code = GlowProfile.objects.create(user=awa, referral_code="AWA12345").referral_code
    invite = APIClient().get(f"/api/v1/glow/invite/{code}").json()
    assert invite == {"name": "Awa", "points": 100}
    assert APIClient().get("/api/v1/glow/invite/NOPE").status_code == 400
    linked = signed_in(adult("Fifamè")).post(
        "/api/v1/glow/referral", {"code": code}, format="json", **H
    )
    assert linked.status_code == 201


def test_routine_and_reminders():
    client = signed_in(adult())
    saved = client.put(
        "/api/v1/glow/routine",
        {"morning": ["Nettoyer", "Hydrater"], "evening": ["Démaquiller"]},
        format="json",
        **H,
    ).json()
    step = saved["morning"][0]["id"]
    ticked = client.post(f"/api/v1/glow/routine/{step}", {"done": True}, format="json", **H)
    assert ticked.json()["morning"][0]["done"] is True
    reminders = client.put(
        "/api/v1/glow/reminders",
        {
            "routine_reminders": True,
            "morning_at": "07:00",
            "evening_at": "21:30",
            "celebration_reminders": False,
        },
        format="json",
        **H,
    ).json()
    assert (reminders["morning_at"], reminders["routine_reminders"]) == ("07:00", True)


def test_calendar_and_rankings_are_public():
    rows = APIClient().get("/api/v1/glow/celebrations?country=BJ").json()
    assert rows and all(row["days_left"] >= 0 for row in rows)
    ranking = APIClient().get("/api/v1/glow/rankings").json()
    assert ranking["rows"] == []
