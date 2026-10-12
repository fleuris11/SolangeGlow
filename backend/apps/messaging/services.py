"""Messaging: starting conversations, sending, receipts, requests, away messages, alerts."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.media.models import MediaAsset
from apps.core.selectors import get_setting
from apps.moderation import services as moderation
from apps.moderation.selectors import can_post, is_blocked_between
from apps.notifications.services import notify

from . import errors, fraud, realtime, selectors, shares
from .models import AwayMessage, Conversation, ConversationMember, Message, QuickReply
from .payloads import message_payload

Member = ConversationMember
MEDIA_PURPOSES = {"message_photo": Message.Kind.PHOTO, "voice_note": Message.Kind.VOICE}


# --- Conversations ---------------------------------------------------------------------------


def start_direct(sender, recipient) -> Conversation:
    """The conversation of two people, created on the first « Write »; no message yet."""
    existing = selectors.direct_between(sender, recipient)
    if existing is not None:
        mine = existing.members.filter(user=sender).first()
        theirs = existing.members.filter(user=recipient).first()
        if theirs and theirs.status == Member.Status.DECLINED:
            raise errors.RequestDeclined()
        if is_blocked_between(sender, recipient):
            raise errors.Blocked()
        if mine and mine.status in (Member.Status.LEFT, Member.Status.DECLINED):
            mine.status = Member.Status.ACTIVE
            mine.save(update_fields=["status", "updated_at"])
        return existing
    status = selectors.start_status(sender, recipient)
    try:
        with transaction.atomic():
            conversation = Conversation.objects.create(
                kind=Conversation.Kind.DIRECT,
                direct_key=selectors.direct_key(sender, recipient),
                created_by=sender,
            )
            Member.objects.create(conversation=conversation, user=sender)
            Member.objects.create(conversation=conversation, user=recipient, status=status)
    except IntegrityError:  # both wrote at the same moment
        return selectors.direct_between(sender, recipient)
    return conversation


def create_group(
    creator,
    people,
    *,
    title: str,
    purpose: str = Conversation.Purpose.CHAT,
    context_type: str = "",
    context_id=None,
    staff=(),
) -> Conversation:
    """A group conversation (dispute room of the payments, support). Used by other apps."""
    everyone = {p.pk: p for p in [*people, *staff, *([creator] if creator else [])]}
    limit = int(get_setting("messaging.group_max_members", default=10))
    if len(everyone) > limit:
        raise errors.TooManyMembers(details={"max": limit})
    staff_ids = {p.pk for p in staff}
    with transaction.atomic():
        conversation = Conversation.objects.create(
            kind=Conversation.Kind.GROUP,
            purpose=purpose,
            title=title[:120],
            context_type=context_type,
            context_id=context_id,
            created_by=creator,
        )
        Member.objects.bulk_create(
            Member(
                conversation=conversation,
                user=person,
                role=Member.Role.STAFF if pk in staff_ids else Member.Role.MEMBER,
            )
            for pk, person in everyone.items()
        )
    return conversation


def send_system(conversation: Conversation, text: str) -> Message:
    """An information line written by the platform (« Dispute opened »…)."""
    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation, kind=Message.Kind.SYSTEM, text=text[:2000]
        )
        Conversation.objects.filter(pk=conversation.pk).update(last_message_at=message.created_at)
    _after_send(message, sender=None)
    return message


def accept_request(user, conversation_id) -> ConversationMember:
    member = selectors.membership(user, conversation_id)
    if member.status == Member.Status.REQUESTED:
        member.status = Member.Status.ACTIVE
        member.save(update_fields=["status", "updated_at"])
        others = [m.user_id for m in selectors.other_members(member.conversation, user)]
        realtime.send_to(
            others,
            {"type": "conversation", "conversation": str(conversation_id), "status": "accepted"},
        )
    return member


def decline_request(user, conversation_id) -> None:
    """She does not want to talk: the sender cannot write again (and is not told why)."""
    member = selectors.membership(user, conversation_id)
    if member.status == Member.Status.REQUESTED:
        member.status = Member.Status.DECLINED
        member.save(update_fields=["status", "updated_at"])


def set_preferences(user, conversation_id, *, muted=None, archived=None) -> ConversationMember:
    member = selectors.membership(user, conversation_id)
    if muted is not None:
        member.muted = muted
    if archived is not None:
        member.archived = archived
    member.save(update_fields=["muted", "archived", "updated_at"])
    return member


# --- Sending -----------------------------------------------------------------------------------


def _check_can_send(sender, member: ConversationMember, others) -> None:
    conversation = member.conversation
    if conversation.is_closed:
        raise errors.ConversationClosed()
    if not can_post(sender):
        raise errors.Restricted()
    if conversation.kind != Conversation.Kind.DIRECT:
        return
    other = others[0] if others else None
    if other is None:
        raise errors.ConversationNotFound()
    if other.status == Member.Status.DECLINED:
        raise errors.RequestDeclined()
    if is_blocked_between(sender, other.user):
        raise errors.Blocked()
    if other.status == Member.Status.REQUESTED:
        allowed = int(get_setting("messaging.request_max_messages", default=1))
        sent = Message.objects.filter(conversation=conversation, sender=sender).count()
        if sent >= allowed:
            raise errors.RequestPending()


def _media(sender, media_id) -> tuple[MediaAsset, str]:
    asset = MediaAsset.objects.filter(pk=media_id, owner=sender).first()
    if asset is None or asset.purpose not in MEDIA_PURPOSES:
        raise errors.InvalidMedia()
    if not asset.is_ready:
        raise errors.MediaNotReady()
    return asset, MEDIA_PURPOSES[asset.purpose]


def send(
    sender,
    conversation_id,
    *,
    text: str = "",
    media_id=None,
    share: dict | None = None,
    client_id=None,
) -> Message:
    """Sends a message. Sending again with the same client_id returns the first message."""
    if client_id:
        existing = Message.objects.filter(sender=sender, client_id=client_id).first()
        if existing is not None:
            return existing
    member = selectors.membership(sender, conversation_id)
    conversation = member.conversation
    others = list(selectors.other_members(conversation, sender))
    _check_can_send(sender, member, others)

    text = (text or "").strip()
    limit = int(get_setting("messaging.max_text_length", default=2000))
    if len(text) > limit:
        raise errors.MessageTooLong(details={"max": limit})
    values = {"text": text, "kind": Message.Kind.TEXT}
    if share:
        share_id, share_data = shares.resolve(sender, share.get("kind", ""), share)
        values.update(
            kind=Message.Kind.SHARE,
            share_kind=share["kind"],
            share_id=share_id,
            share_data=share_data,
        )
    elif media_id:
        asset, kind = _media(sender, media_id)
        values.update(kind=kind, media=asset)
    elif not text:
        raise errors.EmptyMessage()

    labels = []
    dealt = any(fraud.dealt_together(sender, m.user) for m in others)
    if conversation.purpose == Conversation.Purpose.CHAT and text and not dealt:
        labels = fraud.check(text)

    try:
        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                client_id=client_id,
                fraud_labels=labels,
                **values,
            )
            conversation.last_message_at = message.created_at
            conversation.payment_warning = conversation.payment_warning or bool(labels)
            conversation.save(update_fields=["last_message_at", "payment_warning", "updated_at"])
            # Answering a request accepts it.
            member.status = Member.Status.ACTIVE
            member.read_up_to = member.delivered_up_to = message.created_at
            member.archived = False
            member.save(
                update_fields=["status", "read_up_to", "delivered_up_to", "archived", "updated_at"]
            )
            Member.objects.filter(conversation=conversation, archived=True).update(archived=False)
    except IntegrityError:  # the same client_id arrived twice at the same moment
        return Message.objects.get(sender=sender, client_id=client_id)

    _after_send(message, sender=sender, others=others)
    _maybe_send_away(conversation, sender, others)
    return message


def _after_send(message: Message, *, sender, others=None) -> None:
    conversation = message.conversation
    if others is None:
        others = list(
            Member.objects.filter(conversation=conversation).exclude(
                status__in=[Member.Status.LEFT, Member.Status.DECLINED]
            )
        )
    recipients = [m for m in others if m.status != Member.Status.DECLINED]

    def after_commit():
        everyone = [m.user_id for m in recipients] + ([sender.pk] if sender else [])
        realtime.send_to(everyone, {"type": "message", "message": message_payload(message)})
        for member in recipients:
            if sender is not None and member.user_id == sender.pk:
                continue
            push_unread(member.user)
            schedule_notification(member)

    transaction.on_commit(after_commit)


def _maybe_send_away(conversation: Conversation, sender, others) -> None:
    """Outside her opening hours, a pro answers once with her away message."""
    if conversation.kind != Conversation.Kind.DIRECT or not others:
        return
    pro_member = others[0]
    away = AwayMessage.objects.filter(user=pro_member.user, enabled=True).first()
    if away is None or pro_member.status != Member.Status.ACTIVE:
        return
    from apps.pros.hours import opening_status
    from apps.pros.models import ProProfile

    pro = (
        ProProfile.objects.filter(user=pro_member.user, status=ProProfile.Status.PUBLISHED)
        .select_related("country")
        .prefetch_related("opening_periods", "closures")
        .first()
    )
    if pro is None:
        return
    status = opening_status(pro)
    if not status.has_hours or status.is_open:
        return
    hours = int(get_setting("messaging.away_cooldown_hours", default=12))
    now = timezone.now()
    if pro_member.away_sent_at and (now - pro_member.away_sent_at).total_seconds() < hours * 3600:
        return
    with translation.override(pro_member.user.preferred_language):
        text = away.text or gettext(
            "Thank you for your message. I am not available right now: I will answer as soon "
            "as I am back."
        )
    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation, sender=pro_member.user, text=text, is_automatic=True
        )
        Conversation.objects.filter(pk=conversation.pk).update(last_message_at=message.created_at)
        Member.objects.filter(pk=pro_member.pk).update(away_sent_at=now)
    sender_member = Member.objects.filter(conversation=conversation, user=sender).first()
    _after_send(message, sender=pro_member.user, others=[sender_member] if sender_member else [])


def delete_message(user, message_id) -> Message:
    message = Message.objects.select_related("conversation").filter(pk=message_id).first()
    if message is None or not selectors.is_member(user, message.conversation_id):
        raise errors.MessageNotFound()
    if message.sender_id != user.pk or message.is_automatic:
        raise errors.NotYours()
    if message.deleted_at is None:
        message.deleted_at = timezone.now()
        message.save(update_fields=["deleted_at", "updated_at"])
        members = Member.objects.filter(conversation=message.conversation).values_list(
            "user_id", flat=True
        )
        realtime.send_to(members, {"type": "message", "message": message_payload(message)})
    return message


def report_message(user, message_id, *, reason: str, comment: str = ""):
    message = Message.objects.filter(pk=message_id).first()
    if message is None or not selectors.is_member(user, message.conversation_id):
        raise errors.MessageNotFound()
    return moderation.report(user, message, reason=reason, comment=comment)


# --- Receipts, typing, presence -------------------------------------------------------------


def _send_receipt(member: ConversationMember) -> None:
    others = Member.objects.filter(conversation_id=member.conversation_id).exclude(
        user_id=member.user_id
    )
    realtime.send_to(
        others.values_list("user_id", flat=True),
        {
            "type": "receipt",
            "conversation": str(member.conversation_id),
            "user": str(member.user_id),
            "delivered_up_to": member.delivered_up_to.isoformat()
            if member.delivered_up_to
            else None,
            "read_up_to": member.read_up_to.isoformat() if member.read_up_to else None,
        },
    )


def mark_read(user, conversation_id) -> ConversationMember:
    member = selectors.membership(user, conversation_id)
    now = timezone.now()
    member.read_up_to = now
    member.delivered_up_to = now
    member.save(update_fields=["read_up_to", "delivered_up_to", "updated_at"])
    _send_receipt(member)
    push_unread(user)
    return member


def mark_delivered(user) -> int:
    """Her device got the new messages: « received » for the senders."""
    now = timezone.now()
    members = list(
        Member.objects.filter(
            user=user,
            status__in=[Member.Status.ACTIVE, Member.Status.REQUESTED],
            conversation__last_message_at__isnull=False,
        ).select_related("conversation")
    )
    changed = [
        m
        for m in members
        if m.delivered_up_to is None or m.delivered_up_to < m.conversation.last_message_at
    ]
    for member in changed:
        member.delivered_up_to = now
        member.save(update_fields=["delivered_up_to", "updated_at"])
        _send_receipt(member)
    return len(changed)


def typing(user, conversation_id) -> None:
    if not selectors.is_member(user, conversation_id):
        return
    others = (
        Member.objects.filter(conversation_id=conversation_id, status=Member.Status.ACTIVE)
        .exclude(user=user)
        .values_list("user_id", flat=True)
    )
    realtime.send_to(
        others, {"type": "typing", "conversation": str(conversation_id), "user": str(user.pk)}
    )


def presence_changed(user, online: bool) -> None:
    realtime.send_to(
        selectors.partner_ids(user),
        {
            "type": "presence",
            "user": str(user.pk),
            "online": online,
            "last_seen": realtime.last_seen(user.pk),
        },
    )


def push_unread(user) -> None:
    realtime.send_to(
        [user.pk],
        {
            "type": "unread",
            "count": selectors.unread_conversation_count(user),
            "requests": selectors.request_count(user),
        },
    )


# --- Alerts (grouped) -------------------------------------------------------------------------


def schedule_notification(member: ConversationMember) -> None:
    """One alert for several messages: sent a little later, only if still unread."""
    if member.muted or member.status not in (Member.Status.ACTIVE, Member.Status.REQUESTED):
        return
    if realtime.is_viewing(member.user_id, member.conversation_id):
        return
    scheduled = Member.objects.filter(pk=member.pk, notify_scheduled=False).update(
        notify_scheduled=True
    )
    if not scheduled:
        return
    from .tasks import notify_unread

    delay = int(get_setting("messaging.notify_delay_seconds", default=60))
    notify_unread.apply_async(args=[str(member.pk)], countdown=delay)


def notify_unread(member_id) -> bool:
    """Push / e-mail (her preferences) when she is not in the app: « 3 new messages »."""
    member = Member.objects.select_related("conversation", "user").filter(pk=member_id).first()
    if member is None:
        return False
    Member.objects.filter(pk=member.pk).update(notify_scheduled=False)
    if member.muted or member.status not in (Member.Status.ACTIVE, Member.Status.REQUESTED):
        return False
    if realtime.is_online(member.user_id):
        return False  # the app is open: the live counter is enough
    unread = selectors.unread_messages(member).select_related("sender").order_by("-created_at")
    count = unread.count()
    if not count:
        return False
    from .payloads import person_payload

    last = unread.first()
    name = person_payload(last.sender)["name"] if last.sender else gettext("Solange Glow")
    event = (
        "messaging.request"
        if member.status == Member.Status.REQUESTED
        else "messaging.new_messages"
    )
    notify(
        member.user,
        event,
        {"name": name, "count": count},
        link=f"/messages/{member.conversation_id}",
    )
    Member.objects.filter(pk=member.pk).update(last_notified_at=timezone.now())
    return True


# --- Tools of the pros -------------------------------------------------------------------------


def _require_pro(user) -> None:
    from apps.pros.models import ProProfile

    if not ProProfile.objects.filter(user=user).exists():
        raise errors.NotAPro()


def save_quick_replies(user, texts: list[str]) -> list[QuickReply]:
    """Replaces her saved answers, in this order."""
    _require_pro(user)
    texts = [t.strip()[:500] for t in texts if t and t.strip()]
    limit = int(get_setting("messaging.quick_replies_max", default=20))
    if len(texts) > limit:
        raise errors.TooManyQuickReplies(details={"max": limit})
    with transaction.atomic():
        QuickReply.objects.filter(user=user).delete()
        return QuickReply.objects.bulk_create(
            QuickReply(user=user, text=text, position=index) for index, text in enumerate(texts)
        )


def set_away_message(user, *, enabled: bool, text: str) -> AwayMessage:
    _require_pro(user)
    away, _ = AwayMessage.objects.update_or_create(
        user=user, defaults={"enabled": enabled, "text": text.strip()[:500]}
    )
    return away
