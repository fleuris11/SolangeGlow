"""Calls in the messaging: who may call, tokens without any phone number, ringing, missed,
declined, hung up, the length limit, the three-way call of a dispute room, the call log."""

import datetime

import jwt
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import FeatureFlag
from apps.messaging import calls, errors, services
from apps.messaging.models import Call, CallParticipant, ConversationMember, Message
from apps.moderation.services import block
from apps.notifications.models import Notification

from .factories import adult, pro

pytestmark = pytest.mark.django_db
C = Call.Status
H = {"HTTP_X_SG_CLIENT": "web"}


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = timezone.now()

        def move(self, **delta):
            self.value = self.value + datetime.timedelta(**delta)

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def pair():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    ConversationMember.objects.filter(conversation=conversation).update(
        status=ConversationMember.Status.ACTIVE
    )
    return awa, aicha, conversation


def events(user):
    return set(Notification.objects.filter(user=user).values_list("event_key", flat=True))


def call_lines(conversation):
    return list(
        Message.objects.filter(conversation=conversation, kind=Message.Kind.CALL).select_related(
            "call"
        )
    )


def test_who_may_call(fake_livekit):
    awa, aicha, conversation = pair()
    assert calls.call_state(awa, conversation)["can_call"]

    ConversationMember.objects.filter(conversation=conversation, user=aicha).update(
        status=ConversationMember.Status.REQUESTED
    )
    with pytest.raises(errors.CallNeedsAcceptedChat):
        calls.start_call(awa, conversation, video=False)
    ConversationMember.objects.filter(conversation=conversation).update(
        status=ConversationMember.Status.ACTIVE
    )

    aicha.accept_calls = False
    aicha.save()
    with pytest.raises(errors.DoesNotTakeCalls):
        calls.start_call(awa, conversation, video=False)
    assert calls.call_state(awa, conversation)["reason"] == "does_not_take_calls"
    aicha.accept_calls = True
    aicha.save()

    block(aicha, awa)
    with pytest.raises(errors.Blocked):
        calls.start_call(awa, conversation, video=False)

    other, _x, chat = pair()
    FeatureFlag.objects.filter(key="calls").update(is_enabled=False)
    from django.core.cache import cache

    cache.clear()
    with pytest.raises(errors.CallsClosed):
        calls.start_call(other, chat, video=False)
    with pytest.raises(errors.ConversationNotFound):
        calls.call_state(adult("Curieuse"), conversation)


def test_calls_need_livekit(settings):
    awa, _aicha, conversation = pair()
    with pytest.raises(errors.CallsUnavailable):
        calls.start_call(awa, conversation, video=False)


def test_a_call_rings_is_answered_and_hung_up(fake_livekit, clock):
    awa, aicha, conversation = pair()
    call = calls.start_call(awa, conversation, video=True)
    assert call.status == C.RINGING and call.room == f"call-{call.pk}"
    assert fake_livekit.sent("CreateRoom")[0]["max_participants"] == 2
    assert "messaging.call_incoming" in events(aicha)
    assert calls.start_call(aicha, conversation, video=False).pk == call.pk  # one at a time

    token = calls.access(awa, call)["token"]
    claims = jwt.decode(token, fake_livekit.api_secret, algorithms=["HS256"])
    assert claims["sub"] == str(awa.pk) and claims["video"]["room"] == call.room
    assert claims["video"]["canPublishSources"] == ["microphone", "camera"]
    assert str(awa.phone) not in str(claims) and str(aicha.phone) not in str(claims)

    clock.move(seconds=10)
    calls.answer(aicha, call)
    call.refresh_from_db()
    assert call.status == C.ONGOING and call.ends_by == call.answered_at + datetime.timedelta(
        minutes=60
    )
    clock.move(minutes=3)
    calls.hang_up(awa, call)
    call.refresh_from_db()
    assert call.status == C.ENDED and call.duration_seconds == 180
    line = call_lines(conversation)[0]
    assert line.call_id == call.pk
    assert fake_livekit.sent("DeleteRoom")[-1]["room"] == call.room
    with pytest.raises(errors.CallOver):
        calls.access(awa, call)


def test_audio_calls_send_no_camera(fake_livekit):
    awa, aicha, conversation = pair()
    call = calls.start_call(awa, conversation, video=False)
    claims = jwt.decode(
        calls.access(aicha, call)["token"], fake_livekit.api_secret, algorithms=["HS256"]
    )
    assert claims["video"]["canPublishSources"] == ["microphone"]
    with pytest.raises(errors.CallNotFound):
        calls.get_call(adult("Curieuse"), call.pk)


def test_declined_missed_and_cancelled_calls(fake_livekit, clock):
    awa, aicha, conversation = pair()
    call = calls.start_call(awa, conversation, video=False)
    calls.decline(aicha, call)
    call.refresh_from_db()
    assert call.status == C.DECLINED

    missed = calls.start_call(awa, conversation, video=False)
    clock.move(seconds=40)
    assert calls.run_minutely()["missed"] == 0
    clock.move(seconds=10)
    assert calls.run_minutely()["missed"] == 1
    missed.refresh_from_db()
    assert missed.status == C.MISSED
    assert "messaging.call_missed" in events(aicha)

    cancelled = calls.start_call(awa, conversation, video=False)
    calls.hang_up(awa, cancelled)
    cancelled.refresh_from_db()
    assert cancelled.status == C.CANCELLED
    assert [line.call.status for line in call_lines(conversation)] == [
        C.DECLINED,
        C.MISSED,
        C.CANCELLED,
    ]


def test_a_call_is_cut_after_the_longest_length(fake_livekit, clock):
    awa, aicha, conversation = pair()
    call = calls.start_call(awa, conversation, video=False)
    calls.answer(aicha, call)
    clock.move(minutes=61)
    assert calls.run_minutely()["cut"] == 1
    call.refresh_from_db()
    assert call.status == C.ENDED and call.duration_seconds == 61 * 60


def test_three_way_call_of_a_dispute_room(fake_livekit):
    buyer, seller, staff = adult("Awa"), pro("Gloria Make-up"), adult("Équipe", is_staff=True)
    room = services.create_group(
        None, [buyer, seller], title="Litige", purpose="dispute", staff=[staff]
    )
    call = calls.start_call(staff, room, video=False)
    assert fake_livekit.sent("CreateRoom")[0]["max_participants"] == 3
    assert {p.user_id for p in call.participants.all()} == {buyer.pk, seller.pk, staff.pk}
    calls.answer(buyer, call)
    calls.answer(seller, call)
    call.refresh_from_db()
    assert call.status == C.ONGOING
    calls.hang_up(buyer, call)
    call.refresh_from_db()
    assert call.status == C.ONGOING  # two people still talk
    with pytest.raises(errors.CallNotFound):
        calls.get_call(adult("Intruse"), call.pk)
    calls.hang_up(seller, call)
    call.refresh_from_db()
    assert call.status == C.ENDED  # alone: over
    chat = services.create_group(None, [buyer, seller], title="Groupe")
    with pytest.raises(errors.CannotCall):
        calls.start_call(buyer, chat, video=False)


def test_a_full_call_refuses_one_more(fake_livekit):
    buyer, seller, staff = adult("Awa"), pro("Gloria Make-up"), adult("Équipe", is_staff=True)
    room = services.create_group(
        None, [buyer, seller], title="Litige", purpose="dispute", staff=[staff]
    )
    call = calls.start_call(staff, room, video=False)
    Call.objects.filter(pk=call.pk).update(max_people=2)
    call.refresh_from_db()
    calls.answer(buyer, call)
    with pytest.raises(errors.CallFull):
        calls.access(seller, call)


def test_a_dropped_phone_ends_the_call(fake_livekit):
    awa, aicha, conversation = pair()
    call = calls.start_call(awa, conversation, video=False)
    calls.answer(aicha, call)
    calls.on_webhook(
        "participant_left",
        {"room": {"name": call.room}, "participant": {"identity": str(aicha.pk)}},
    )
    call.refresh_from_db()
    assert call.status == C.ENDED
    assert CallParticipant.objects.get(call=call, user=aicha).state == "left"
    ringing = calls.start_call(awa, conversation, video=False)
    calls.on_webhook("room_finished", {"room": {"name": ringing.room}})
    ringing.refresh_from_db()
    assert ringing.status == C.MISSED


def test_the_call_api(fake_livekit):
    awa, aicha, conversation = pair()
    me, her = APIClient(), APIClient()
    me.force_authenticate(awa)
    her.force_authenticate(aicha)
    url = reverse("v1:conversation-call", args=[conversation.pk])
    assert me.get(url).json() == {"active": None, "can_call": True, "reason": None}
    started = me.post(url, {"video": True}, format="json", **H).json()
    assert started["call"]["kind"] == "video" and started["call"]["mine"]
    assert started["access"]["url"] == fake_livekit.url
    call_id = started["call"]["id"]
    state = her.get(url).json()
    assert state["active"]["id"] == call_id and state["active"]["my_state"] == "invited"
    assert state["active"]["people"][0]["name"]
    answered = her.post(reverse("v1:call-answer", args=[call_id]), **H).json()
    assert answered["call"]["status"] == "ongoing" and answered["access"]["token"]
    ended = her.post(reverse("v1:call-hang-up", args=[call_id]), **H).json()
    assert ended["status"] == "ended"
    log = me.get(reverse("v1:call-log")).json()
    assert [c["id"] for c in log["results"]] == [call_id]
    messages = me.get(reverse("v1:conversation-messages", args=[conversation.pk])).json()
    assert messages["results"][-1]["call"]["status"] == "ended"
    declined = me.post(url, {"video": False}, format="json", **H).json()["call"]["id"]
    assert her.post(reverse("v1:call-decline", args=[declined]), **H).json()["status"] == (
        "declined"
    )
    assert me.get(reverse("v1:call", args=[declined])).json()["status"] == "declined"
