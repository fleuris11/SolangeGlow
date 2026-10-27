"""The live room: going on air, tokens (who films, who watches), questions, raised hands,
limits (length, places, free lives of the month), webhooks and the replay."""

import datetime

import jwt
import pytest
from django.utils import timezone

from apps.academy.models import LiveSession
from apps.academy.services import lives as academy_lives
from apps.academy.tests.factories import trainer
from apps.core.media.models import MediaAsset
from apps.core.tests.factories import PlatformSettingFactory
from apps.live import errors, services
from apps.live.models import LiveHand, LiveQuestion, LiveRoom
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
T = "training"


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = timezone.now()

        def move(self, **delta):
            self.value = self.value + datetime.timedelta(**delta)

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def planned(pro=None, *, minutes_ahead=5, duration=60):
    pro = pro or trainer()
    return academy_lives.plan_live(
        pro.user,
        title="Vos questions de mariée",
        starts_at=timezone.now() + datetime.timedelta(minutes=minutes_ahead),
        duration_minutes=duration,
        capacity=50,
    )


def registered(live, name="Awa"):
    student = adult(name)
    academy_lives.register(student, live)
    return student


def grant(access, fake):
    return jwt.decode(access["token"], fake.api_secret, algorithms=["HS256"])["video"]


def events(user):
    return set(Notification.objects.filter(user=user).values_list("event_key", flat=True))


def on_air(fake, live=None):
    live = live or planned()
    student = registered(live)
    services.start(live.pro.user, T, live.pk)
    return live, student


def test_the_host_goes_on_air_in_her_window(fake_livekit, clock):
    live = planned(minutes_ahead=60)
    student = registered(live)
    with pytest.raises(errors.NotHost):
        services.start(student, T, live.pk)
    with pytest.raises(errors.TooEarly):
        services.start(live.pro.user, T, live.pk)
    clock.move(minutes=50)
    room = services.start(live.pro.user, T, live.pk)
    assert room.status == LiveRoom.Status.ON_AIR and room.max_viewers == 300
    assert room.ends_by == room.started_at + datetime.timedelta(minutes=120)
    created = fake_livekit.sent("CreateRoom")[0]
    assert created["name"] == room.name and created["max_participants"] == 305
    assert services.start(live.pro.user, T, live.pk).pk == room.pk  # twice: same room
    live.refresh_from_db()
    assert live.status == LiveSession.Status.LIVE
    assert "academy.live_on_air" in events(student)


def test_tokens_give_each_one_her_part(fake_livekit):
    live = planned()
    student = registered(live)
    with pytest.raises(errors.NotOnAir):
        services.join(student, T, live.pk)
    services.start(live.pro.user, T, live.pk)
    host = services.join(live.pro.user, T, live.pk)
    assert host["host"] and grant(host, fake_livekit)["canPublishSources"] == [
        "camera",
        "microphone",
    ]
    viewer = services.join(student, T, live.pk)
    assert not viewer["host"] and viewer["identity"] == str(student.pk)
    assert grant(viewer, fake_livekit)["canPublish"] is False
    assert viewer["host_identity"] == str(live.pro.user_id)
    with pytest.raises(errors.LiveNotFound):
        services.join(adult("Pas inscrite"), T, live.pk)
    from django.contrib.auth.models import AnonymousUser

    with pytest.raises(errors.LiveNotFound):
        services.join(AnonymousUser(), T, live.pk)


def test_a_full_live_and_a_live_without_video(fake_livekit, settings):
    live, student = on_air(fake_livekit)
    LiveRoom.objects.filter(kind=T, source_id=live.pk).update(viewers=300)
    with pytest.raises(errors.LiveFull):
        services.join(student, T, live.pk)
    assert services.join(live.pro.user, T, live.pk)["host"]  # the host always comes in

    other = planned(trainer("Fatou"))
    from apps.core.providers import livekit

    livekit.use_fake(None)
    with pytest.raises(errors.VideoUnavailable):
        services.start(other.pro.user, T, other.pk)


def test_questions_are_moderated_and_answered_by_the_host(fake_livekit):
    live, student = on_air(fake_livekit)
    with pytest.raises(errors.EmptyQuestion):
        services.ask(student, T, live.pk, "  ")
    question = services.ask(student, T, live.pk, "Quel fond de teint pour peau mixte ?")
    assert fake_livekit.sent("SendData")  # everybody reloads
    with pytest.raises(errors.NotHost):
        services.mark_answered(student, T, live.pk, question.pk)
    services.mark_answered(live.pro.user, T, live.pk, question.pk)
    question.refresh_from_db()
    assert question.answered_at is not None

    LiveQuestion.objects.filter(pk=question.pk).update(visibility="held")
    other = registered(live, "Bintou")
    assert services.state(other, T, live.pk)["questions"] == []
    mine = services.state(student, T, live.pk)["questions"]
    assert mine[0]["held"] and mine[0]["mine"]


def test_raise_the_hand_and_get_the_floor(fake_livekit):
    live, student = on_air(fake_livekit)
    hand = services.raise_hand(student, T, live.pk)
    assert hand.status == LiveHand.Status.RAISED
    with pytest.raises(errors.HandsClosed):
        services.raise_hand(live.pro.user, T, live.pk)
    with pytest.raises(errors.NotHost):
        services.give_floor(student, T, live.pk, student.pk)
    host_view = services.state(live.pro.user, T, live.pk)
    assert host_view["hands"][0]["user_id"] == student.pk

    services.give_floor(live.pro.user, T, live.pk, student.pk)
    update = fake_livekit.sent("UpdateParticipant")[-1]
    assert update["identity"] == str(student.pk)
    assert update["permission"]["can_publish_sources"] == ["MICROPHONE"]
    state = services.state(student, T, live.pk)
    assert state["speaking"] and state["my_hand"] == "speaking"
    assert grant(services.join(student, T, live.pk), fake_livekit)["canPublishSources"] == [
        "microphone"
    ]

    second = registered(live, "Bintou")
    services.raise_hand(second, T, live.pk)
    services.give_floor(live.pro.user, T, live.pk, second.pk)  # one at a time
    assert LiveHand.objects.get(user=student).status == LiveHand.Status.DONE
    services.take_floor(live.pro.user, T, live.pk, second.pk)
    assert fake_livekit.sent("UpdateParticipant")[-1]["permission"]["can_publish"] is False
    assert not services.state(second, T, live.pk)["speaking"]
    with pytest.raises(errors.NoHand):
        services.give_floor(live.pro.user, T, live.pk, second.pk)
    services.raise_hand(student, T, live.pk)
    services.lower_hand(student, T, live.pk)
    assert LiveHand.objects.get(user=student).status == LiveHand.Status.DONE


def test_two_free_lives_a_month_then_premium(fake_livekit, settings):
    pro = trainer()
    planned(pro, minutes_ahead=60 * 24 * 2)
    planned(pro, minutes_ahead=60 * 24 * 2 + 120)
    with pytest.raises(errors.MonthlyLimit) as refused:
        planned(pro, minutes_ahead=60 * 24 * 2 + 240)
    assert refused.value.details["max"] == 2
    PlatformSettingFactory(key="live.free_per_month", value_type="integer", value="3")
    planned(pro, minutes_ahead=60 * 24 * 2 + 240)

    from apps.glowpro.models import Plan
    from apps.glowpro.services import start_trial

    Plan.objects.filter(key="premium").update(
        limits={"campaigns_per_month": 4, "lives_per_month": 10}
    )
    start_trial(pro)
    assert services.monthly_allowance(pro) == 10


def test_too_long_lives_are_cut_and_the_host_ends_hers(fake_livekit, clock):
    live, _student = on_air(fake_livekit)
    clock.move(minutes=119)
    assert services.run_minutely()["cut"] == 0
    clock.move(minutes=2)
    assert services.run_minutely()["cut"] == 1
    room = LiveRoom.objects.get(kind=T, source_id=live.pk)
    assert room.status == LiveRoom.Status.ENDED
    assert fake_livekit.sent("DeleteRoom")[-1]["room"] == room.name
    live.refresh_from_db()
    assert live.status == LiveSession.Status.ENDED
    with pytest.raises(errors.LiveOver):
        services.start(live.pro.user, T, live.pk)


def webhook(name, room, identity="", **extra):
    services.on_webhook(
        name,
        {
            "event": name,
            "room": {"name": room.name},
            "participant": {"identity": identity},
            **extra,
        },
    )


def test_viewers_are_counted_and_the_host_is_recorded(fake_livekit):
    live, student = on_air(fake_livekit)
    room = LiveRoom.objects.get(kind=T, source_id=live.pk)
    webhook("participant_joined", room, str(live.pro.user_id))
    webhook("participant_joined", room, str(student.pk))
    webhook("participant_joined", room, "guest-abc")
    room.refresh_from_db()
    assert room.viewers == 2 and room.peak_viewers == 2 and room.total_viewers == 2
    webhook("participant_left", room, "guest-abc")
    room.refresh_from_db()
    assert room.viewers == 1 and room.peak_viewers == 2

    webhook("track_published", room, str(student.pk))
    assert not fake_livekit.sent("StartParticipantEgress")  # only the host is recorded
    webhook("track_published", room, str(live.pro.user_id))
    started = fake_livekit.sent("StartParticipantEgress")
    assert len(started) == 1 and started[0]["identity"] == str(live.pro.user_id)
    room.refresh_from_db()
    assert room.replay_status == LiveRoom.Replay.RECORDING
    assert started[0]["file_outputs"][0]["filepath"] == f"private/{room.replay.original.name}"

    services.end_by_host(live.pro.user, T, live.pk)
    room.refresh_from_db()
    assert fake_livekit.sent("StopEgress")[0]["egress_id"] == room.egress_id
    assert room.replay_status == LiveRoom.Replay.PROCESSING
    assert room.replay_until is not None
    assert services.state(student, T, live.pk)["replay"]["status"] == "processing"


def test_the_replay_is_for_registered_students_and_expires(fake_livekit, clock, monkeypatch):
    live, student = on_air(fake_livekit)
    room = LiveRoom.objects.get(kind=T, source_id=live.pk)
    webhook("track_published", room, str(live.pro.user_id))
    services.end_by_host(live.pro.user, T, live.pk)
    room.refresh_from_db()
    processed = []
    monkeypatch.setattr(
        "apps.core.media.tasks.process_media_asset.delay", lambda pk: processed.append(pk)
    )
    services.on_webhook(
        "egress_ended",
        {
            "event": "egress_ended",
            "egressInfo": {
                "egressId": room.egress_id,
                "roomName": room.name,
                "status": "EGRESS_COMPLETE",
                "fileResults": [{"size": "123456"}],
            },
        },
    )
    assert processed == [str(room.replay_id)]
    MediaAsset.objects.filter(pk=room.replay_id).update(
        status=MediaAsset.Status.READY,
        duration_seconds=1800,
        variants={"low": {"path": "v/low.mp4"}, "medium": {"path": "v/m.mp4"}},
    )
    assert services.run_minutely()["replays"] == 1
    assert "academy.live_replay" in events(student)
    replay = services.state(student, T, live.pk)["replay"]
    assert replay["status"] == "ready" and set(replay["urls"]) == {"low", "medium"}
    with pytest.raises(errors.LiveNotFound):
        services.state(adult("Pas inscrite"), T, live.pk)

    clock.move(days=31)
    assert services.expire_replays() == 1
    room.refresh_from_db()
    assert room.replay_status == LiveRoom.Replay.EXPIRED and room.replay is None
    assert services.state(student, T, live.pk)["replay"] is None


def test_a_room_closed_by_livekit_ends_the_live(fake_livekit):
    live, _student = on_air(fake_livekit)
    room = LiveRoom.objects.get(kind=T, source_id=live.pk)
    webhook("room_finished", room)
    room.refresh_from_db()
    assert room.status == LiveRoom.Status.ENDED


def test_upcoming_lives_on_the_home_page(fake_livekit):
    later = planned(minutes_ahead=60 * 24)
    now_live, _student = on_air(fake_livekit, planned(trainer("Fatou")))
    found = services.upcoming(later.country)
    assert [item["source_id"] for item in found][:2] == [now_live.pk, later.pk]
    assert found[0]["on_air"] and not found[1]["on_air"]
    assert found[1]["link"] == f"/academie/live/{later.pk}"
