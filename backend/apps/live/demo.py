"""Demo lives (seed_demo): Gloria's sales live tomorrow evening with pinned products, a
sales replay and a training replay (both show the generated lesson video), Awa registered
to Prisca's lives, a call between Awa and Aïcha in the call log."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.academy.models import LiveRegistration, LiveSession
from apps.accounts.models import User
from apps.core.media.models import MediaAsset
from apps.messaging import services as messaging
from apps.messaging.models import Call, CallParticipant, ConversationMember, Message
from apps.pros.models import ProProfile
from apps.shop.models import LivePin, Product, SaleLive

from .models import LiveRoom


def _video() -> MediaAsset | None:
    return (
        MediaAsset.objects.filter(purpose="lesson_video", status=MediaAsset.Status.READY)
        .order_by("created_at")
        .first()
    )


def _ended_room(kind, source_id, host, pro, title, started, video, days) -> None:
    room_id = f"live-demo-{source_id}"
    LiveRoom.objects.get_or_create(
        kind=kind,
        source_id=source_id,
        defaults={
            "name": room_id,
            "host": host,
            "pro": pro,
            "country": pro.country,
            "title": title,
            "status": LiveRoom.Status.ENDED,
            "started_at": started,
            "ended_at": started + datetime.timedelta(minutes=40),
            "max_viewers": 300,
            "peak_viewers": 37,
            "total_viewers": 52,
            "replay_status": LiveRoom.Replay.READY,
            "replay": video,
            "replay_until": timezone.now() + datetime.timedelta(days=days),
        },
    )


def _sales(gloria: ProProfile, video, now) -> int:
    if SaleLive.objects.filter(pro=gloria).exists():
        return 0
    products = list(Product.objects.filter(pro=gloria, status=Product.Status.PUBLISHED)[:3])
    coming = SaleLive.objects.create(
        pro=gloria,
        title="Nouveautés lèvres : gloss et rouges",
        description="Je vous montre les teintes en vrai, posez vos questions.",
        starts_at=(now + datetime.timedelta(days=1)).replace(hour=19),
        duration_minutes=45,
        currency=gloria.currency,
    )
    past = SaleLive.objects.create(
        pro=gloria,
        title="Teint parfait pour la Tabaski",
        starts_at=now - datetime.timedelta(days=2),
        duration_minutes=40,
        status=SaleLive.Status.ENDED,
        orders_count=6,
        revenue_minor=48_000,
        currency=gloria.currency,
    )
    for index, product in enumerate(products):
        LivePin.objects.create(sale_live=coming, product=product, pinned_at=now, unpinned_at=now)
        LivePin.objects.create(
            sale_live=past,
            product=product,
            pinned_at=past.starts_at + datetime.timedelta(minutes=5 * index),
            unpinned_at=past.starts_at + datetime.timedelta(minutes=5 * index + 4),
        )
    if video is not None:
        _ended_room("sale", past.pk, gloria.user, gloria, past.title, past.starts_at, video, 5)
    return 2


def _training(prisca: ProProfile, awa: User | None, video, now) -> int:
    for live in LiveSession.objects.filter(pro=prisca):
        if awa is not None:
            LiveRegistration.objects.get_or_create(live=live, user=awa)
    if LiveSession.objects.filter(pro=prisca, status=LiveSession.Status.ENDED).exists():
        return 0
    past = LiveSession.objects.create(
        pro=prisca,
        author=prisca.user,
        country=prisca.country,
        title="Teint lumineux : questions-réponses",
        starts_at=now - datetime.timedelta(days=3),
        duration_minutes=45,
        capacity=50,
        status=LiveSession.Status.ENDED,
    )
    if awa is not None:
        LiveRegistration.objects.get_or_create(live=past, user=awa)
    for registration in LiveRegistration.objects.filter(live__pro=prisca):
        LiveSession.objects.filter(pk=registration.live_id).update(
            registered_count=LiveRegistration.objects.filter(live_id=registration.live_id).count()
        )
    if video is not None:
        _ended_room("training", past.pk, prisca.user, prisca, past.title, past.starts_at, video, 25)
    return 1


def _call(awa: User | None, aicha: ProProfile | None, now) -> int:
    if awa is None or aicha is None or Call.objects.exists():
        return 0
    conversation = messaging.start_direct(awa, aicha.user)
    ConversationMember.objects.filter(conversation=conversation).update(
        status=ConversationMember.Status.ACTIVE
    )
    started = now - datetime.timedelta(days=1, hours=2)
    call = Call.objects.create(
        conversation=conversation,
        caller=awa,
        kind=Call.Kind.VIDEO,
        status=Call.Status.ENDED,
        room=f"call-demo-{conversation.pk}",
        ring_until=started + datetime.timedelta(seconds=45),
        answered_at=started,
        ended_at=started + datetime.timedelta(minutes=4, seconds=12),
    )
    for user in (awa, aicha.user):
        CallParticipant.objects.create(
            call=call, user=user, state=CallParticipant.State.LEFT, joined_at=started
        )
    Message.objects.create(
        conversation=conversation, sender=awa, kind=Message.Kind.CALL, call=call, is_automatic=True
    )
    return 1


def seed_live() -> dict:
    now = timezone.now().replace(second=0, microsecond=0)
    video = _video()
    pros = {
        p.slug: p
        for p in ProProfile.objects.filter(slug__in=["gloria", "institut-prisca", "aicha"])
    }
    awa = User.objects.filter(phone="+2290197000201").first()
    counts = {"lives": 0, "calls": 0}
    with transaction.atomic():
        if "gloria" in pros:
            counts["lives"] += _sales(pros["gloria"], video, now)
        if "institut-prisca" in pros:
            counts["lives"] += _training(pros["institut-prisca"], awa, video, now)
        counts["calls"] = _call(awa, pros.get("aicha"), now)
    return counts
