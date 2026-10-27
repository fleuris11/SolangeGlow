"""The live room through the API (the screens) and the back office."""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academy.services import lives as academy_lives
from apps.academy.tests.factories import trainer
from apps.accounts.tests.factories import UserFactory
from apps.live.models import LiveRoom
from apps.messaging import services as messaging
from apps.messaging.models import Call
from apps.messaging.tests.factories import adult, pro

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_a_training_live_through_the_screens(fake_livekit):
    teacher = trainer()
    live = academy_lives.plan_live(
        teacher.user,
        title="Vos questions",
        starts_at=timezone.now() + datetime.timedelta(minutes=5),
        duration_minutes=30,
        capacity=20,
    )
    student = adult("Awa")
    academy_lives.register(student, live)
    host, me = signed_in(teacher.user), signed_in(student)
    args = ["training", live.pk]

    state = me.get(reverse("v1:live-state", args=args)).json()
    assert state["status"] == "scheduled" and state["can_raise_hand"] and not state["can_ask"]
    assert APIClient().get(reverse("v1:live-state", args=args)).status_code == 404
    assert me.post(reverse("v1:live-join", args=args), **H).json()["code"] == "not_on_air"

    started = host.post(reverse("v1:live-start", args=args), **H).json()
    assert started["status"] == "on_air" and started["is_host"]
    joined = me.post(reverse("v1:live-join", args=args), **H).json()
    assert joined["room"].startswith("live-") and joined["url"] == fake_livekit.url

    asked = me.post(
        reverse("v1:live-questions", args=args), {"text": "Et les peaux grasses ?"}, **H
    ).json()
    question = asked["questions"][0]
    assert question["mine"] and question["text"] == "Et les peaux grasses ?"
    answered = host.post(reverse("v1:live-answered", args=[*args, question["id"]]), **H).json()
    assert answered["questions"][0]["answered"]

    raised = me.post(reverse("v1:live-hand", args=args), **H).json()
    assert raised["my_hand"] == "raised"
    floor = reverse("v1:live-floor", args=[*args, student.pk])
    assert host.post(floor, **H).json()["hands"][0]["status"] == "speaking"
    assert me.get(reverse("v1:live-state", args=args)).json()["speaking"]
    host.delete(floor, **H)
    me.post(reverse("v1:live-hand", args=args), **H)
    assert me.delete(reverse("v1:live-hand", args=args), **H).json()["my_hand"] is None

    ended = host.post(reverse("v1:live-end", args=args), **H).json()
    assert ended["status"] == "ended"
    home = APIClient().get(reverse("v1:live-upcoming")).json()
    assert all(item["source_id"] != str(live.pk) for item in home)


@pytest.fixture
def admin_client(client):
    admin = UserFactory(is_staff=True, is_superuser=True, email="admin@example.com")
    client.force_login(admin)
    client.admin = admin
    return client


def test_the_team_cuts_a_live_and_deletes_a_replay(admin_client, fake_livekit):
    teacher = trainer()
    live = academy_lives.plan_live(
        teacher.user,
        title="Vos questions",
        starts_at=timezone.now() + datetime.timedelta(minutes=5),
        duration_minutes=30,
        capacity=20,
    )
    from apps.live import services

    services.start(teacher.user, "training", live.pk)
    room = LiveRoom.objects.get(source_id=live.pk)
    assert admin_client.get(reverse("admin:live_liveroom_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:live_liveroom_change", args=[room.pk])).status_code == (
        200
    )
    admin_client.get(reverse("admin:live_liveroom_cut_detail", args=[room.pk]))
    room.refresh_from_db()
    assert room.status == LiveRoom.Status.ENDED and room.ended_by_staff
    admin_client.get(reverse("admin:live_liveroom_cut_detail", args=[room.pk]))  # already over
    admin_client.get(reverse("admin:live_liveroom_delete_replay_detail", args=[room.pk]))
    LiveRoom.objects.filter(pk=room.pk).update(replay_status=LiveRoom.Replay.READY)
    admin_client.get(reverse("admin:live_liveroom_delete_replay_detail", args=[room.pk]))
    room.refresh_from_db()
    assert room.replay_status == LiveRoom.Replay.EXPIRED
    assert admin_client.get(reverse("admin:live_livequestion_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:shop_salelive_changelist")).status_code == 200


def test_the_team_starts_the_three_way_call_of_a_dispute(admin_client, fake_livekit, settings):
    buyer, seller = adult("Awa"), pro("Gloria Make-up")
    room = messaging.create_group(None, [buyer, seller], title="Litige", purpose="dispute")
    answer = admin_client.get(reverse("admin:messaging_conversation_call_detail", args=[room.pk]))
    call = Call.objects.get(conversation=room)
    assert answer.status_code == 302 and answer["Location"].endswith(f"/fr/appel/{call.pk}")
    assert call.participants.count() == 3
    assert admin_client.get(reverse("admin:messaging_call_changelist")).status_code == 200
