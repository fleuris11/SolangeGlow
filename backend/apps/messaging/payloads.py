"""What the web app receives for a person, a message and a conversation (API and live)."""

from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext

from apps.core.media.services import asset_payload

from . import realtime
from .models import ConversationMember, Message


def person_payload(user, *, with_presence: bool = False) -> dict:
    from apps.social.serializers import member_name

    try:
        pro = user.pro_profile
    except ObjectDoesNotExist:
        pro = None
    published = pro is not None and pro.is_published
    photo = (pro.photo if published and pro.photo_id else None) or user.photo
    data = {
        "id": str(user.pk),
        "name": (pro.display_name if published else "") or member_name(user),
        "photo": asset_payload(photo) if photo is not None and photo.is_ready else None,
        "is_pro": published,
        "pro_slug": pro.slug if published else None,
        "verified": bool(published and pro.is_verified),
    }
    if with_presence:
        data["online"] = realtime.is_online(user.pk)
        data["last_seen"] = realtime.last_seen(user.pk)
    return data


def message_payload(message: Message, viewer=None) -> dict:
    removed = message.deleted_at is not None or (
        message.visibility != Message.Visibility.VISIBLE
        and (viewer is None or message.sender_id != viewer.pk)
    )
    if message.deleted_at is not None:
        state = "deleted"
    elif message.visibility == Message.Visibility.REMOVED:
        state = "removed"
    elif message.visibility == Message.Visibility.HELD:
        state = "held"
    else:
        state = "visible"
    return {
        "id": str(message.pk),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id) if message.sender_id else None,
        "kind": message.kind,
        "text": "" if removed else message.text,
        "media": None if removed else asset_payload(message.media),
        "share": None
        if removed or not message.share_kind
        else {"kind": message.share_kind, "id": str(message.share_id), **message.share_data},
        "client_id": str(message.client_id) if message.client_id else None,
        "fraud_labels": message.fraud_labels,
        "is_automatic": message.is_automatic,
        "state": state,
        "created_at": message.created_at.isoformat(),
    }


def receipts_payload(members) -> dict:
    """When the others received and read: the oldest mark of the group counts."""
    listening = (ConversationMember.Status.ACTIVE, ConversationMember.Status.REQUESTED)
    others = [m for m in members if m.status in listening]
    delivered = [m.delivered_up_to for m in others]
    read = [m.read_up_to for m in others]
    return {
        "delivered_up_to": min(delivered).isoformat() if others and all(delivered) else None,
        "read_up_to": min(read).isoformat() if others and all(read) else None,
    }


def conversation_payload(member: ConversationMember, *, others, last_message=None, unread=0):
    conversation = member.conversation
    people = [person_payload(m.user, with_presence=True) for m in others]
    if conversation.title:
        title = conversation.title
    elif people:
        title = ", ".join(p["name"] for p in people)
    else:
        title = gettext("Conversation")
    return {
        "id": str(conversation.pk),
        "kind": conversation.kind,
        "purpose": conversation.purpose,
        "title": title,
        "people": people,
        "status": member.status,
        "unread": unread,
        "muted": member.muted,
        "is_closed": conversation.is_closed,
        "payment_warning": conversation.payment_warning,
        "last_message": message_payload(last_message, member.user) if last_message else None,
        "last_message_at": conversation.last_message_at.isoformat()
        if conversation.last_message_at
        else None,
        "receipts": receipts_payload(list(others)),
        "waiting_for_answer": any(m.status == ConversationMember.Status.REQUESTED for m in others),
    }
