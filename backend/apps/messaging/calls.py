"""Audio and video calls in the messaging (ADR-013), through LiveKit: nobody sees anybody's
phone number. Two people in a conversation they both accepted, or three in a dispute room
(buyer, seller, a member of the team). Nothing is recorded; the call log keeps who, when
and how long, and a line in the conversation (« Video call, 3 min », « Missed call »).

Ringing: the people called get a live event (incoming call screen) and a notification;
nobody answers within `calls.ring_seconds`: missed. A call is cut after `calls.max_minutes`.
"""

from __future__ import annotations

import datetime
import logging
import uuid

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.core.providers import livekit
from apps.core.providers.base import ProviderError, ProviderNotConfigured
from apps.core.selectors import get_setting, is_feature_enabled
from apps.moderation.selectors import can_post, is_blocked_between
from apps.notifications.services import notify

from . import errors, realtime
from .models import Call, CallParticipant, Conversation, ConversationMember, Message
from .payloads import call_line, person_payload

logger = logging.getLogger("solangeglow.calls")

PREFIX = "call-"
C = Call.Status
P = CallParticipant.State
Member = ConversationMember
OPEN = (C.RINGING, C.ONGOING)


def _setting(key: str, default, country=None):
    return int(get_setting(key, country=getattr(country, "code", country), default=default))


def _link(call: Call) -> str:
    return f"/appel/{call.pk}"


# --- Who may call -------------------------------------------------------------------------


def _members(conversation: Conversation, user) -> tuple[Member, list[Member]]:
    rows = list(
        Member.objects.filter(conversation=conversation).select_related(
            "user", "user__photo", "user__pro_profile", "user__pro_profile__photo"
        )
    )
    mine = next((m for m in rows if m.user_id == user.pk), None)
    if mine is None or mine.status in (Member.Status.LEFT, Member.Status.DECLINED):
        raise errors.ConversationNotFound()
    return mine, [m for m in rows if m.user_id != user.pk]


def check_can_call(user, conversation: Conversation) -> list[Member]:
    """The people she would call, or the reason why she cannot."""
    if not is_feature_enabled("calls", country=user.country_id and user.country):
        raise errors.CallsClosed()
    mine, others = _members(conversation, user)
    if conversation.is_closed:
        raise errors.ConversationClosed()
    if not can_post(user):
        raise errors.Restricted()
    if conversation.kind == Conversation.Kind.DIRECT:
        if conversation.purpose != Conversation.Purpose.CHAT or len(others) != 1:
            raise errors.CannotCall()
        other = others[0]
        if mine.status != Member.Status.ACTIVE or other.status != Member.Status.ACTIVE:
            raise errors.CallNeedsAcceptedChat()
        if is_blocked_between(user, other.user):
            raise errors.Blocked()
        if not other.user.accept_calls or not other.user.is_active:
            raise errors.DoesNotTakeCalls()
        return others
    if conversation.purpose != Conversation.Purpose.DISPUTE:
        raise errors.CannotCall()
    active = [m for m in others if m.status == Member.Status.ACTIVE and m.user.is_active]
    if not active:
        raise errors.CannotCall()
    return active


def active_call(conversation: Conversation) -> Call | None:
    return (
        Call.objects.filter(conversation=conversation, status__in=OPEN)
        .order_by("-created_at")
        .first()
    )


def call_state(user, conversation: Conversation) -> dict:
    """For the conversation screen: the call going on, and whether she may start one."""
    _members(conversation, user)
    call = active_call(conversation)
    reason = None
    try:
        check_can_call(user, conversation)
    except DomainError as exc:
        reason = exc.code
    return {
        "active": call_payload(call, user) if call else None,
        "can_call": reason is None,
        "reason": reason,
    }


# --- Payloads -----------------------------------------------------------------------------


def call_payload(call: Call, user) -> dict:
    people = list(call.participants.select_related("user", "user__photo"))
    mine = next((p for p in people if p.user_id == user.pk), None)
    return {
        **call_line(call),
        "conversation_id": str(call.conversation_id),
        "is_dispute": call.conversation.purpose == Conversation.Purpose.DISPUTE,
        "mine": call.caller_id == user.pk,
        "my_state": mine.state if mine else None,
        "people": [
            {**person_payload(p.user), "state": p.state} for p in people if p.user_id != user.pk
        ],
        "ring_until": call.ring_until,
        "answered_at": call.answered_at,
        "ended_at": call.ended_at,
        "ends_by": call.ends_by,
        "created_at": call.created_at,
    }


def _push(call: Call, *, event: str = "call") -> None:
    """Tells every device of the people in the call that it changed."""
    ids = list(call.participants.values_list("user_id", flat=True))
    data = {
        "type": event,
        "call": {
            **call_line(call),
            "conversation_id": str(call.conversation_id),
        },
    }
    transaction.on_commit(lambda: realtime.send_to(ids, data))


# --- Starting, answering, hanging up ------------------------------------------------------


def _client():
    try:
        return livekit.client()
    except ProviderNotConfigured as exc:
        raise errors.CallsUnavailable() from exc


@transaction.atomic
def start_call(user, conversation: Conversation, *, video: bool) -> Call:
    Conversation.objects.select_for_update().filter(pk=conversation.pk).first()
    others = check_can_call(user, conversation)
    current = active_call(conversation)
    if current is not None:
        return current  # one call at a time: she joins it
    country = user.country if user.country_id else None
    is_group = conversation.kind != Conversation.Kind.DIRECT
    max_people = _setting("calls.max_participants", 3, country) if is_group else 2
    if is_group and len(others) + 1 > max_people:
        others = [m for m in others if m.role == Member.Role.MEMBER][: max_people - 1]
    now = timezone.now()
    call_id = uuid.uuid4()
    call = Call.objects.create(
        id=call_id,
        conversation=conversation,
        caller=user,
        kind=Call.Kind.VIDEO if video else Call.Kind.AUDIO,
        room=f"{PREFIX}{call_id}",
        ring_until=now + datetime.timedelta(seconds=_setting("calls.ring_seconds", 45, country)),
        max_people=max_people,
    )
    CallParticipant.objects.create(call=call, user=user, state=P.JOINED, joined_at=now)
    CallParticipant.objects.bulk_create(CallParticipant(call=call, user=m.user) for m in others)
    try:
        _client().create_room(call.room, max_participants=max_people, empty_timeout=60)
    except ProviderError as exc:
        raise errors.CallsUnavailable() from exc
    record("messaging.call_started", call, actor=user, metadata={"kind": call.kind})
    _push(call, event="call_incoming")
    name = person_payload(user)["name"]
    for member in others:
        transaction.on_commit(
            lambda u=member.user: notify(
                u,
                "messaging.call_incoming",
                {"name": name, "kind": call.get_kind_display()},
                link=_link(call),
            )
        )
    return call


def get_call(user, call_id) -> Call:
    call = (
        Call.objects.select_related("conversation", "caller")
        .filter(pk=call_id, participants__user=user)
        .first()
    )
    if call is None:
        raise errors.CallNotFound()
    return call


def _locked(call: Call) -> Call:
    return Call.objects.select_for_update().select_related("conversation").get(pk=call.pk)


def access(user, call: Call) -> dict:
    """Her token for the room of the call (camera only in a video call)."""
    if call.status not in OPEN:
        raise errors.CallOver()
    me = CallParticipant.objects.filter(call=call, user=user).first()
    if me is None or me.state == P.DECLINED:
        raise errors.CallNotFound()
    joined = CallParticipant.objects.filter(call=call, state=P.JOINED).exclude(user=user).count()
    if joined + 1 > call.max_people:
        raise errors.CallFull(details={"max": call.max_people})
    sources = [livekit.MICROPHONE] + ([livekit.CAMERA] if call.kind == Call.Kind.VIDEO else [])
    country = call.caller.country if call.caller and call.caller.country_id else None
    ttl = _setting("rtc.token_ttl_seconds", 600, country)
    lk = _client()
    token = lk.token(
        room=call.room,
        identity=str(user.pk),
        name=person_payload(user)["name"],
        ttl=ttl,
        sources=sources,
    )
    return {
        "url": lk.url,
        "room": call.room,
        "token": token,
        "identity": str(user.pk),
        "expires_at": timezone.now() + datetime.timedelta(seconds=ttl),
    }


@transaction.atomic
def answer(user, call: Call) -> Call:
    call = _locked(call)
    if call.status not in OPEN:
        raise errors.CallOver()
    me = CallParticipant.objects.select_for_update().filter(call=call, user=user).first()
    if me is None:
        raise errors.CallNotFound()
    now = timezone.now()
    if me.state != P.JOINED:
        me.state, me.joined_at, me.left_at = P.JOINED, now, None
        me.save(update_fields=["state", "joined_at", "left_at", "updated_at"])
    if call.status == C.RINGING and user.pk != call.caller_id:  # she rejoins her own call
        country = call.caller.country if call.caller and call.caller.country_id else None
        call.status = C.ONGOING
        call.answered_at = now
        call.ends_by = now + datetime.timedelta(minutes=_setting("calls.max_minutes", 60, country))
        call.save(update_fields=["status", "answered_at", "ends_by", "updated_at"])
    _push(call)
    return call


@transaction.atomic
def decline(user, call: Call) -> Call:
    call = _locked(call)
    if call.status not in OPEN:
        return call
    me = CallParticipant.objects.filter(call=call, user=user).first()
    if me is None:
        raise errors.CallNotFound()
    if call.caller_id == user.pk:
        return hang_up(user, call)
    me.state = P.DECLINED
    me.save(update_fields=["state", "updated_at"])
    waiting = call.participants.filter(state=P.INVITED).exists()
    if call.status == C.RINGING and not waiting:
        _finish(call, C.DECLINED)
    else:
        _push(call)
    return call


@transaction.atomic
def hang_up(user, call: Call) -> Call:
    call = _locked(call)
    if call.status not in OPEN:
        return call
    now = timezone.now()
    CallParticipant.objects.filter(call=call, user=user, state=P.JOINED).update(
        state=P.LEFT, left_at=now
    )
    still = call.participants.filter(state=P.JOINED).count()
    if call.status == C.RINGING and call.caller_id == user.pk:
        _finish(call, C.CANCELLED)
    elif still <= 1:
        _finish(call, C.ENDED)
    else:
        _push(call)
    return call


def _finish(call: Call, status: str) -> None:
    """Ends the call, writes the line of the conversation, closes the room."""
    now = timezone.now()
    if status == C.ENDED and call.answered_at is None:
        status = C.CANCELLED
    call.status = status
    call.ended_at = now
    call.save(update_fields=["status", "ended_at", "updated_at"])
    CallParticipant.objects.filter(call=call, state=P.JOINED).update(state=P.LEFT, left_at=now)
    message = Message.objects.create(
        conversation=call.conversation,
        sender=call.caller,
        kind=Message.Kind.CALL,
        call=call,
        is_automatic=True,
    )
    Conversation.objects.filter(pk=call.conversation_id).update(last_message_at=message.created_at)
    record(
        "messaging.call_ended", call, metadata={"status": status, "seconds": call.duration_seconds}
    )
    _push(call)
    if status in (C.MISSED, C.CANCELLED):
        missed = list(call.participants.filter(state=P.INVITED).select_related("user"))
        name = person_payload(call.caller)["name"] if call.caller else ""
        for person in missed:
            transaction.on_commit(
                lambda u=person.user: notify(
                    u,
                    "messaging.call_missed",
                    {"name": name},
                    link=f"/messages/{call.conversation_id}",
                )
            )
    room = call.room

    def close():
        try:
            livekit.client().delete_room(room)
        except (ProviderError, ProviderNotConfigured):
            logger.info("Call room not deleted at LiveKit (it closes when empty)")

    transaction.on_commit(close)


# --- By itself (Celery Beat, every minute) ------------------------------------------------


def run_minutely(now=None) -> dict:
    now = now or timezone.now()
    missed = cut = 0
    for call in Call.objects.filter(status=C.RINGING, ring_until__lte=now):
        with transaction.atomic():
            call = _locked(call)
            if call.status == C.RINGING:
                _finish(call, C.MISSED)
                missed += 1
    for call in Call.objects.filter(status=C.ONGOING, ends_by__lte=now):
        with transaction.atomic():
            call = _locked(call)
            if call.status == C.ONGOING:
                _finish(call, C.ENDED)
                cut += 1
    return {"missed": missed, "cut": cut}


# --- Webhooks of LiveKit: somebody's phone dropped, the room closed -------------------------


def on_webhook(name: str, event: dict) -> None:
    call = Call.objects.filter(room=livekit.room_of(event)).first()
    if call is None or call.status not in OPEN:
        return
    identity = (event.get("participant") or {}).get("identity", "")
    with transaction.atomic():
        call = _locked(call)
        if call.status not in OPEN:
            return
        if name == "participant_left" and _is_uuid(identity):
            CallParticipant.objects.filter(call=call, user_id=identity, state=P.JOINED).update(
                state=P.LEFT, left_at=timezone.now()
            )
            if call.status == C.ONGOING and call.participants.filter(state=P.JOINED).count() <= 1:
                _finish(call, C.ENDED)
            else:
                _push(call)
        elif name == "room_finished":
            _finish(call, C.ENDED if call.status == C.ONGOING else C.MISSED)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def call_log(user):
    """Her calls, newest first (the screen « My calls »)."""
    return (
        Call.objects.filter(participants__user=user)
        .exclude(status__in=OPEN)
        .select_related("conversation", "caller")
        .order_by("-created_at")
    )
