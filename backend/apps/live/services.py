"""The live room (ADR-013): going on air, joining with a token, written questions, raised
hands, limits (length, places, free lives of the month), the replay.

Each change is pushed to the devices in the room through LiveKit (an event that tells
them to reload); the screens also reload by themselves every few seconds.
"""

from __future__ import annotations

import calendar
import datetime
import logging
import uuid

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.media.services import variant_url
from apps.core.providers import livekit
from apps.core.providers.base import ProviderError, ProviderNotConfigured
from apps.core.selectors import get_setting
from apps.moderation import services as moderation
from apps.moderation.selectors import can_post

from . import errors, registry
from .models import LiveAttendance, LiveHand, LiveQuestion, LiveRoom

logger = logging.getLogger("solangeglow.live")

S = LiveRoom.Status
R = LiveRoom.Replay
PREFIX = "live-"


def setting(key: str, country=None, default=None):
    return get_setting(key, country=getattr(country, "code", country), default=default)


def _signed_in(user) -> bool:
    return user is not None and user.is_authenticated


def identity_of(user) -> str:
    return str(user.pk) if _signed_in(user) else f"guest-{uuid.uuid4().hex[:12]}"


# --- Rooms --------------------------------------------------------------------------------


def source_and_plan(kind: str, source_id):
    source = registry.get(kind)
    plan = source.planned(source_id) if source else None
    if plan is None:
        raise errors.LiveNotFound()
    return source, plan


def room_for(kind: str, plan: registry.Planned) -> LiveRoom:
    """The room of a planned live, created the first time somebody needs it."""
    room = LiveRoom.objects.filter(kind=kind, source_id=plan.source_id).first()
    if room is not None:
        return room
    room_id = uuid.uuid4()
    room, _created = LiveRoom.objects.get_or_create(
        kind=kind,
        source_id=plan.source_id,
        defaults={
            "id": room_id,
            "name": f"{PREFIX}{room_id}",
            "host": plan.host,
            "pro": plan.pro,
            "country": plan.country,
            "title": plan.title[:120],
        },
    )
    return room


def is_host(user, plan: registry.Planned) -> bool:
    return _signed_in(user) and plan.host.pk == user.pk


def _locked(room: LiveRoom) -> LiveRoom:
    return LiveRoom.objects.select_for_update().get(pk=room.pk)


def push(room: LiveRoom, kind: str, **data) -> None:
    """Tells every device in the room that something changed (after commit, never fails)."""
    if room.status != S.ON_AIR:
        return
    name = room.name

    def send():
        try:
            livekit.client().send(name, {"type": kind, **data})
        except (ProviderError, ProviderNotConfigured):
            logger.info("Live event not sent (%s)", kind)

    transaction.on_commit(send)


# --- Going on air -------------------------------------------------------------------------


@transaction.atomic
def start(user, kind: str, source_id) -> LiveRoom:
    source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan):
        raise errors.NotHost()
    if plan.cancelled:
        raise errors.LiveNotFound()
    room = _locked(room_for(kind, plan))
    if room.status == S.ON_AIR:
        return room
    if room.status == S.ENDED:
        raise errors.LiveOver()
    now = timezone.now()
    early = int(setting("live.start_early_minutes", plan.country, 15))
    if now < plan.starts_at - datetime.timedelta(minutes=early):
        raise errors.TooEarly(details={"minutes": early})
    if now >= plan.ends_at:
        raise errors.LiveOver()
    max_minutes = int(setting("live.max_minutes", plan.country, 120))
    room.max_viewers = int(setting("live.max_viewers", plan.country, 300))
    try:
        livekit.client().create_room(
            room.name, max_participants=room.max_viewers + 5, empty_timeout=300
        )
    except (ProviderError, ProviderNotConfigured) as exc:
        raise errors.VideoUnavailable() from exc
    room.status = S.ON_AIR
    room.started_at = now
    room.ends_by = now + datetime.timedelta(minutes=max_minutes)
    room.title = plan.title[:120]
    room.save()
    record("live.started", room, actor=user)
    transaction.on_commit(lambda: source.started(plan.source_id, room))
    return room


@transaction.atomic
def end(room: LiveRoom, *, by=None, staff: bool = False, reason: str = "host") -> LiveRoom:
    room = _locked(room)
    if room.status != S.ON_AIR:
        if room.status == S.WAITING and staff:
            room.status = S.ENDED
            room.ended_at = timezone.now()
            room.ended_by_staff = True
            room.save()
        return room
    now = timezone.now()
    lk = livekit.client() if livekit.available() else None
    if room.egress_id and room.replay_status == R.RECORDING:
        try:
            if lk:
                lk.stop_recording(room.egress_id)
            room.replay_status = R.PROCESSING
        except ProviderError:
            logger.warning("Recording not stopped", exc_info=True)
            room.replay_status = R.PROCESSING  # the egress stops by itself with the room
    source = registry.get(room.kind)
    if room.replay_status in (R.RECORDING, R.PROCESSING) and source:
        days = int(source.replay_days(room.country))
        room.replay_until = now + datetime.timedelta(days=days)
    room.status = S.ENDED
    room.ended_at = now
    room.speaker_identity = ""
    room.viewers = 0
    room.ended_by_staff = staff
    room.save()
    LiveAttendance.objects.filter(room=room, left_at__isnull=True).update(left_at=now)
    LiveHand.objects.filter(room=room).exclude(status=LiveHand.Status.DONE).update(
        status=LiveHand.Status.DONE
    )
    record("live.ended", room, actor=by, metadata={"reason": reason, "staff": staff})
    name = room.name

    def close():
        if source:
            source.ended(room.source_id, room)
        try:
            if lk:
                lk.delete_room(name)
        except ProviderError:
            logger.info("Room not deleted at LiveKit (it closes when empty)")

    transaction.on_commit(close)
    return room


def end_by_host(user, kind: str, source_id) -> LiveRoom:
    _source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan):
        raise errors.NotHost()
    return end(room_for(kind, plan), by=user)


# --- Joining ------------------------------------------------------------------------------


def join(user, kind: str, source_id) -> dict:
    """A token for the room: the host films and speaks, the others watch (and speak when
    they have the floor)."""
    source, plan = source_and_plan(kind, source_id)
    host = is_host(user, plan)
    if not host:
        if not _signed_in(user) and not source.guests:
            raise errors.LiveNotFound()
        if not source.can_watch(user, plan.source_id):
            raise errors.LiveNotFound()
    room = room_for(kind, plan)
    if room.status == S.ENDED:
        raise errors.LiveOver()
    if room.status != S.ON_AIR:
        raise errors.NotOnAir()
    if not host and room.viewers >= room.max_viewers:
        raise errors.LiveFull(details={"max": room.max_viewers})
    identity = identity_of(user)
    if host:
        sources = [livekit.CAMERA, livekit.MICROPHONE]
    elif room.speaker_identity and room.speaker_identity == identity:
        sources = [livekit.MICROPHONE]
    else:
        sources = []
    ttl = int(setting("rtc.token_ttl_seconds", plan.country, 600))
    try:
        lk = livekit.client()
    except ProviderNotConfigured as exc:
        raise errors.VideoUnavailable() from exc
    name = (user.first_name or "") if _signed_in(user) else ""
    token = lk.token(room=room.name, identity=identity, name=name, ttl=ttl, sources=sources)
    return {
        "url": lk.url,
        "room": room.name,
        "token": token,
        "identity": identity,
        "host": host,
        "host_identity": str(plan.host.pk),
        "expires_at": timezone.now() + datetime.timedelta(seconds=ttl),
    }


# --- Questions ----------------------------------------------------------------------------


def _on_air_room(user, kind: str, source_id) -> tuple[registry.LiveSource, object, LiveRoom]:
    source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan) and not source.can_watch(user, plan.source_id):
        raise errors.LiveNotFound()
    room = room_for(kind, plan)
    if room.status != S.ON_AIR:
        raise errors.NotOnAir()
    return source, plan, room


def ask(user, kind: str, source_id, text: str) -> LiveQuestion:
    if not _signed_in(user):
        raise errors.SignInToAsk()
    _source, _plan, room = _on_air_room(user, kind, source_id)
    if not can_post(user):
        raise errors.CannotAsk()
    text = (text or "").strip()
    if not text or len(text) > 300:
        raise errors.EmptyQuestion()
    at = int((timezone.now() - room.started_at).total_seconds()) if room.started_at else 0
    question = LiveQuestion.objects.create(room=room, author=user, text=text, at_second=max(0, at))
    moderation.screen(question, text=text)
    push(room, "questions")
    return question


def mark_answered(user, kind: str, source_id, question_id) -> LiveQuestion:
    _source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan):
        raise errors.NotHost()
    room = room_for(kind, plan)
    question = LiveQuestion.objects.filter(pk=question_id, room=room).first()
    if question is None:
        raise errors.LiveNotFound()
    if question.answered_at is None:
        question.answered_at = timezone.now()
        question.save(update_fields=["answered_at", "updated_at"])
        push(room, "questions")
    return question


def visible_questions(room: LiveRoom, user):
    """Visible questions, and hers while they wait for a review."""
    visible = Q(visibility=LiveQuestion.Visibility.VISIBLE)
    if _signed_in(user):
        visible |= Q(author=user, visibility=LiveQuestion.Visibility.HELD)
    rows = LiveQuestion.objects.filter(room=room).filter(visible).select_related("author")
    return rows.order_by("-created_at")[:100]


# --- Raised hands -------------------------------------------------------------------------


@transaction.atomic
def raise_hand(user, kind: str, source_id) -> LiveHand:
    if not _signed_in(user):
        raise errors.SignInToAsk()
    source, plan, room = _on_air_room(user, kind, source_id)
    if not source.hands or is_host(user, plan):
        raise errors.HandsClosed()
    hand = LiveHand.objects.select_for_update().filter(room=room, user=user).first()
    if hand is None:
        hand = LiveHand.objects.create(
            room=room, user=user, status=LiveHand.Status.RAISED, raised_at=timezone.now()
        )
    elif hand.status == LiveHand.Status.DONE:
        hand.status = LiveHand.Status.RAISED
        hand.raised_at = timezone.now()
        hand.save(update_fields=["status", "raised_at", "updated_at"])
    push(room, "hands")
    return hand


@transaction.atomic
def lower_hand(user, kind: str, source_id) -> None:
    """She lowers her hand, or gives the floor back."""
    if not _signed_in(user):
        raise errors.SignInToAsk()
    _source, _plan, room = _on_air_room(user, kind, source_id)
    hand = LiveHand.objects.select_for_update().filter(room=room, user=user).first()
    if hand is None or hand.status == LiveHand.Status.DONE:
        return
    if hand.status == LiveHand.Status.SPEAKING:
        _silence(_locked(room), hand)
    else:
        hand.status = LiveHand.Status.DONE
        hand.save(update_fields=["status", "updated_at"])
    push(room, "hands")


def _silence(room: LiveRoom, hand: LiveHand) -> None:
    identity = str(hand.user_id)
    hand.status = LiveHand.Status.DONE
    hand.save(update_fields=["status", "updated_at"])
    if room.speaker_identity == identity:
        room.speaker_identity = ""
        room.save(update_fields=["speaker_identity", "updated_at"])
    try:
        livekit.client().set_sources(room.name, identity, [])
    except (ProviderError, ProviderNotConfigured):
        logger.info("Floor not taken back at LiveKit (she may have left)")


@transaction.atomic
def give_floor(user, kind: str, source_id, user_id) -> LiveHand:
    """Her microphone opens; whoever had the floor gives it back."""
    _source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan):
        raise errors.NotHost()
    room = _locked(room_for(kind, plan))
    if room.status != S.ON_AIR:
        raise errors.NotOnAir()
    hand = LiveHand.objects.select_for_update().filter(room=room, user_id=user_id).first()
    if hand is None or hand.status == LiveHand.Status.DONE:
        raise errors.NoHand()
    if hand.status == LiveHand.Status.SPEAKING:
        return hand
    for other in LiveHand.objects.filter(room=room, status=LiveHand.Status.SPEAKING):
        _silence(room, other)
    try:
        livekit.client().set_sources(room.name, str(hand.user_id), [livekit.MICROPHONE])
    except (ProviderError, ProviderNotConfigured) as exc:
        raise errors.VideoUnavailable() from exc
    hand.status = LiveHand.Status.SPEAKING
    hand.save(update_fields=["status", "updated_at"])
    room.speaker_identity = str(hand.user_id)
    room.save(update_fields=["speaker_identity", "updated_at"])
    record("live.floor_given", room, actor=user, metadata={"to": str(hand.user_id)})
    push(room, "hands")
    return hand


@transaction.atomic
def take_floor(user, kind: str, source_id, user_id) -> None:
    _source, plan = source_and_plan(kind, source_id)
    if not is_host(user, plan):
        raise errors.NotHost()
    room = _locked(room_for(kind, plan))
    hand = LiveHand.objects.select_for_update().filter(room=room, user_id=user_id).first()
    if hand is None:
        raise errors.NoHand()
    if hand.status == LiveHand.Status.SPEAKING:
        _silence(room, hand)
    elif hand.status == LiveHand.Status.RAISED:
        hand.status = LiveHand.Status.DONE
        hand.save(update_fields=["status", "updated_at"])
    push(room, "hands")


# --- Free lives of the month --------------------------------------------------------------


def month_bounds(moment: datetime.datetime) -> tuple[datetime.datetime, datetime.datetime]:
    local = timezone.localtime(moment)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days = calendar.monthrange(local.year, local.month)[1]
    return start, start + datetime.timedelta(days=days)


def monthly_allowance(pro) -> int:
    from apps.glowpro.selectors import limit

    plan_limit = limit(pro, "lives_per_month")
    if plan_limit is not None:
        return plan_limit
    return int(setting("live.free_per_month", pro.country, 2))


def check_quota(pro, starts_at: datetime.datetime) -> None:
    """A pro plans a limited number of lives each month (training and sales together)."""
    if pro is None:
        return  # the platform's lives
    start, stop = month_bounds(starts_at)
    used = sum(source.count_in_month(pro, start, stop) for source in registry.all_sources())
    allowed = monthly_allowance(pro)
    if used >= allowed:
        raise errors.MonthlyLimit(details={"max": allowed})


# --- What she sees ------------------------------------------------------------------------


def _replay(room: LiveRoom, now) -> dict | None:
    if room.replay_status in (R.NONE, R.EXPIRED, R.FAILED):
        return None
    if room.replay_until and room.replay_until <= now:
        return None
    asset = room.replay
    if room.replay_status != R.READY or asset is None or asset.status != MediaAsset.Status.READY:
        return {"status": "processing", "until": room.replay_until, "urls": {}, "duration": None}
    ttl = int(asset.duration_seconds or 0) + 1800
    urls = {
        name: url
        for name in ("low", "medium", "poster")
        if (url := variant_url(asset, name, ttl=ttl))
    }
    return {
        "status": "ready",
        "until": room.replay_until,
        "urls": urls,
        "duration": asset.duration_seconds,
    }


def _host_payload(plan: registry.Planned) -> dict:
    from apps.core.media.services import asset_payload

    pro = plan.pro
    if pro is None:
        return {"name": "Solange Glow", "slug": None, "photo": None}
    photo = pro.photo if pro.photo is not None and pro.photo.is_ready else None
    return {"name": pro.display_name, "slug": pro.slug, "photo": asset_payload(photo)}


def _status(plan: registry.Planned, room: LiveRoom) -> str:
    if room.status == S.ON_AIR:
        return "on_air"
    if room.status == S.ENDED:
        return "ended"
    if plan.cancelled:
        return "cancelled"
    return "scheduled"


def state(user, kind: str, source_id) -> dict:
    source, plan = source_and_plan(kind, source_id)
    host = is_host(user, plan)
    room = room_for(kind, plan)
    now = timezone.now()
    status = _status(plan, room)
    allowed = host or source.can_watch(user, plan.source_id)
    if status == "ended":
        allowed = host or source.can_replay(user, plan.source_id)
    if not allowed and not source.guests:
        # A training live: only the waiting-room details of the academy page.
        raise errors.LiveNotFound()
    identity = str(user.pk) if _signed_in(user) else ""
    my_hand = None
    hands = []
    if _signed_in(user) and source.hands:
        mine = LiveHand.objects.filter(room=room, user=user).first()
        my_hand = mine.status if mine and mine.status != LiveHand.Status.DONE else None
        if host:
            hands = [
                {
                    "user_id": hand.user_id,
                    "name": hand.user.first_name or "",
                    "status": hand.status,
                    "raised_at": hand.raised_at,
                }
                for hand in LiveHand.objects.filter(room=room)
                .exclude(status=LiveHand.Status.DONE)
                .select_related("user")
            ]
    questions = []
    if allowed:
        questions = [
            {
                "id": q.pk,
                "name": q.author.first_name or "",
                "text": q.text,
                "at_second": q.at_second,
                "answered": q.answered_at is not None,
                "mine": _signed_in(user) and q.author_id == user.pk,
                "held": q.visibility != LiveQuestion.Visibility.VISIBLE,
                "created_at": q.created_at,
            }
            for q in visible_questions(room, user)
        ]
    early = int(setting("live.start_early_minutes", plan.country, 15))
    return {
        "kind": kind,
        "source_id": plan.source_id,
        "title": plan.title,
        "status": status,
        "starts_at": plan.starts_at,
        "ends_at": plan.ends_at,
        "time_zone": plan.country.timezone,
        "can_start_at": plan.starts_at - datetime.timedelta(minutes=early),
        "started_at": room.started_at,
        "ends_by": room.ends_by,
        "host": _host_payload(plan),
        "is_host": host,
        "can_watch": allowed,
        "can_ask": allowed and _signed_in(user) and status == "on_air" and not host,
        "can_raise_hand": allowed and _signed_in(user) and source.hands and not host,
        "signed_in": _signed_in(user),
        "viewers": room.viewers,
        "max_viewers": room.max_viewers,
        "speaking": bool(identity) and room.speaker_identity == identity,
        "my_hand": my_hand,
        "hands": hands,
        "questions": questions,
        "replay": _replay(room, now) if allowed else None,
        "link": plan.link,
        "cover_url": plan.cover_url,
        "sale": source.extras(plan.source_id, room, user),
    }


def upcoming(country, limit: int = 8) -> list[dict]:
    """Lives on air and coming soon in her country (home page), training and sales."""
    now = timezone.now()
    items = []
    for source in registry.all_sources():
        for plan in source.upcoming(country, now, limit):
            room = LiveRoom.objects.filter(kind=source.kind, source_id=plan.source_id).first()
            if room and room.status == S.ENDED:
                continue
            items.append((source.kind, plan, room is not None and room.status == S.ON_AIR))
    items.sort(key=lambda item: (not item[2], item[1].starts_at))
    return [
        {
            "kind": kind,
            "source_id": plan.source_id,
            "title": plan.title,
            "starts_at": plan.starts_at,
            "time_zone": plan.country.timezone,
            "on_air": on_air,
            "host": _host_payload(plan),
            "link": plan.link,
            "cover_url": plan.cover_url,
        }
        for kind, plan, on_air in items[:limit]
    ]


# --- By itself ----------------------------------------------------------------------------


def run_minutely(now=None) -> dict:
    """Cuts the lives that went past the longest length; marks the replays that are ready."""
    now = now or timezone.now()
    cut = 0
    for room in LiveRoom.objects.filter(status=S.ON_AIR, ends_by__lte=now):
        end(room, reason="too_long")
        cut += 1
    ready = 0
    rows = LiveRoom.objects.filter(replay_status=R.PROCESSING, replay__isnull=False).select_related(
        "replay"
    )
    for room in rows:
        if room.replay.status == MediaAsset.Status.READY:
            room.replay_status = R.READY
            room.save(update_fields=["replay_status", "updated_at"])
            source = registry.get(room.kind)
            if source and hasattr(source, "replay_ready"):
                source.replay_ready(room.source_id, room)
            ready += 1
        elif room.replay.status in (MediaAsset.Status.FAILED, MediaAsset.Status.REJECTED):
            room.replay_status = R.FAILED
            room.save(update_fields=["replay_status", "updated_at"])
    return {"cut": cut, "replays": ready}


def expire_replays(now=None) -> int:
    """Replays past their time are deleted (storage costs)."""
    from apps.core.media.services import delete_asset

    now = now or timezone.now()
    count = 0
    rows = LiveRoom.objects.filter(replay_until__lte=now).exclude(replay_status=R.EXPIRED)
    for room in rows.select_related("replay"):
        delete_replay(room, delete_asset=delete_asset)
        count += 1
    return count


def delete_replay(room: LiveRoom, *, by=None, delete_asset=None) -> None:
    if delete_asset is None:
        from apps.core.media.services import delete_asset
    asset = room.replay
    room.replay = None
    room.replay_status = R.EXPIRED
    room.save(update_fields=["replay", "replay_status", "updated_at"])
    if asset is not None and asset.purpose == "live_replay":
        delete_asset(asset)  # never a video of another use (the demo shows a lesson)
    record("live.replay_deleted", room, actor=by)


# --- Webhooks of LiveKit ------------------------------------------------------------------


def _count(room: LiveRoom) -> None:
    open_rows = LiveAttendance.objects.filter(room=room, left_at__isnull=True).exclude(
        identity=str(room.host_id)
    )
    viewers = open_rows.values("identity").distinct().count()
    total = (
        LiveAttendance.objects.filter(room=room)
        .exclude(identity=str(room.host_id))
        .aggregate(n=Count("identity", distinct=True))["n"]
    )
    LiveRoom.objects.filter(pk=room.pk).update(
        viewers=viewers, total_viewers=total, peak_viewers=max(room.peak_viewers, viewers)
    )


def _start_recording(room: LiveRoom) -> None:
    try:
        lk = livekit.client()
    except ProviderNotConfigured:
        return
    if not lk.egress:
        return
    with transaction.atomic():
        room = _locked(room)
        if room.egress_id or room.status != S.ON_AIR:
            return
        asset = MediaAsset(
            id=uuid.uuid4(),
            owner=room.host,
            kind=MediaAsset.Kind.VIDEO,
            purpose="live_replay",
            visibility=MediaAsset.Visibility.PRIVATE,
            original_name="replay.mp4",
            content_type="video/mp4",
            status=MediaAsset.Status.PENDING,
        )
        # The recording service writes the file straight where the original belongs.
        asset.original.name = f"originals/video/{asset.pk}/original.mp4"
        try:
            egress_id = lk.record(room.name, str(room.host_id), f"private/{asset.original.name}")
        except ProviderError:
            logger.warning("Recording not started", exc_info=True)
            return
        asset.save()
        room.egress_id = egress_id
        room.replay = asset
        room.replay_status = R.RECORDING
        room.save(update_fields=["egress_id", "replay", "replay_status", "updated_at"])


def _recording_done(event: dict) -> None:
    info = event.get("egressInfo") or event.get("egress_info") or {}
    egress_id = info.get("egressId") or info.get("egress_id") or ""
    room = LiveRoom.objects.filter(egress_id=egress_id).select_related("replay").first()
    if room is None or room.replay is None:
        return
    status = info.get("status", "")
    results = info.get("fileResults") or info.get("file_results") or []
    asset = room.replay
    if status in ("EGRESS_COMPLETE", 3) and results:
        asset.size_bytes = int(results[0].get("size") or 0)
        asset.save(update_fields=["size_bytes", "updated_at"])
        room.replay_status = R.PROCESSING
        room.save(update_fields=["replay_status", "updated_at"])
        from apps.core.media.tasks import process_media_asset

        transaction.on_commit(lambda: process_media_asset.delay(str(asset.pk)))
    else:
        room.replay_status = R.FAILED
        room.save(update_fields=["replay_status", "updated_at"])


def on_webhook(name: str, event: dict) -> None:
    if name.startswith("egress_"):
        if name == "egress_ended":
            _recording_done(event)
        return
    room = LiveRoom.objects.filter(name=livekit.room_of(event)).first()
    if room is None:
        return
    identity = (event.get("participant") or {}).get("identity", "")
    now = timezone.now()
    if name == "participant_joined" and identity:
        LiveAttendance.objects.create(room=room, identity=identity, joined_at=now)
        _count(room)
    elif name == "participant_left" and identity:
        LiveAttendance.objects.filter(room=room, identity=identity, left_at__isnull=True).update(
            left_at=now
        )
        _count(room)
    elif name == "track_published" and identity == str(room.host_id):
        _start_recording(room)
    elif name == "room_finished" and room.status == S.ON_AIR:
        end(room, reason="room_closed")
