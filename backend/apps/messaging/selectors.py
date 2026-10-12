"""Read-side rules of the messaging: who may write to whom, conversations, unread counts."""

from __future__ import annotations

import datetime

from django.db.models import Count, DateTimeField, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.accounts.selectors import can_receive_message_from, is_visible
from apps.moderation.selectors import is_blocked_between

from . import errors
from .models import Conversation, ConversationMember, Message

EPOCH = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
Member = ConversationMember


def is_pro(user) -> bool:
    from apps.pros.models import ProProfile

    return ProProfile.objects.filter(user=user, status=ProProfile.Status.PUBLISHED).exists()


def follows(follower, followed) -> bool:
    from apps.social.models import Follow

    return Follow.objects.filter(follower=follower, followed=followed).exists()


def start_status(sender, recipient) -> str:
    """How a first message from sender to recipient arrives: directly, or as a request.

    Clients write to pros, pros to pros. Two clients write to each other once they follow
    each other. A pro writing to a client who does not follow her sends a request. Young
    accounts only hear from people they follow (unless the admin allows it).
    """
    if sender.pk == recipient.pk:
        raise errors.CannotWriteYourself()
    if not is_visible(recipient):
        raise errors.PersonNotFound()
    if is_blocked_between(sender, recipient):
        raise errors.Blocked()
    followed_by_recipient = follows(recipient, sender)
    if not can_receive_message_from(recipient, sender, sender_is_followed=followed_by_recipient):
        raise errors.ProtectedAccount()
    if is_pro(recipient):
        return Member.Status.ACTIVE
    if is_pro(sender):
        return Member.Status.ACTIVE if followed_by_recipient else Member.Status.REQUESTED
    if followed_by_recipient and follows(sender, recipient):
        return Member.Status.ACTIVE
    raise errors.MutualFollowNeeded()


def direct_key(user, other) -> str:
    first, second = sorted([str(user.pk), str(other.pk)])
    return f"{first}:{second}"


def direct_between(user, other) -> Conversation | None:
    return Conversation.objects.filter(direct_key=direct_key(user, other)).first()


def membership(user, conversation_id) -> ConversationMember:
    """Her place in the conversation; refuses people who are not (or no longer) in it."""
    member = (
        ConversationMember.objects.select_related("conversation")
        .filter(conversation_id=conversation_id, user=user)
        .exclude(status__in=[Member.Status.LEFT, Member.Status.DECLINED])
        .first()
    )
    if member is None:
        raise errors.ConversationNotFound()
    return member


def other_members(conversation, user):
    return (
        ConversationMember.objects.filter(conversation=conversation)
        .exclude(user=user)
        .select_related("user", "user__photo")
    )


def visible_messages(user):
    """What a member sees: everything visible, and her own messages even when held."""
    return Message.objects.filter(
        Q(visibility=Message.Visibility.VISIBLE) | Q(sender=user)
    ).select_related("media", "sender")


def unread_messages(member: ConversationMember):
    return Message.objects.filter(
        conversation_id=member.conversation_id,
        created_at__gt=member.read_up_to or EPOCH,
        visibility=Message.Visibility.VISIBLE,
        deleted_at__isnull=True,
    ).exclude(sender=member.user_id)


def _unread_subquery():
    return Subquery(
        Message.objects.filter(
            conversation_id=OuterRef("conversation_id"),
            created_at__gt=OuterRef("read_mark"),
            visibility=Message.Visibility.VISIBLE,
            deleted_at__isnull=True,
        )
        .exclude(sender_id=OuterRef("user_id"))
        .order_by()
        .values("conversation_id")
        .annotate(total=Count("pk"))
        .values("total")[:1]
    )


def memberships_of(user, *, box: str = "inbox"):
    """Her conversations, newest first. "requests": messages from people she does not know."""
    status = Member.Status.REQUESTED if box == "requests" else Member.Status.ACTIVE
    return (
        ConversationMember.objects.filter(user=user, status=status, archived=False)
        .filter(conversation__last_message_at__isnull=False)
        .select_related("conversation")
        .annotate(read_mark=Coalesce("read_up_to", Value(EPOCH, output_field=DateTimeField())))
        .annotate(unread=Coalesce(_unread_subquery(), 0))
        .order_by(F("conversation__last_message_at").desc(nulls_last=True), "-pk")
    )


def last_messages(user, conversation_ids) -> dict:
    """The latest message she can see in each conversation (one query, DISTINCT ON)."""
    rows = (
        visible_messages(user)
        .filter(conversation_id__in=conversation_ids)
        .order_by("conversation_id", "-created_at")
        .distinct("conversation_id")
    )
    return {row.conversation_id: row for row in rows}


def unread_conversation_count(user) -> int:
    return (
        memberships_of(user).filter(unread__gt=0).count()
        + ConversationMember.objects.filter(user=user, status=Member.Status.REQUESTED)
        .filter(conversation__last_message_at__isnull=False, read_up_to__isnull=True)
        .count()
    )


def request_count(user) -> int:
    return ConversationMember.objects.filter(
        user=user, status=Member.Status.REQUESTED, conversation__last_message_at__isnull=False
    ).count()


def partner_ids(user) -> set:
    """People she shares a conversation with: they see her presence."""
    conversation_ids = ConversationMember.objects.filter(
        user=user, status=Member.Status.ACTIVE
    ).values("conversation_id")
    return set(
        ConversationMember.objects.filter(
            conversation_id__in=conversation_ids, status=Member.Status.ACTIVE
        )
        .exclude(user=user)
        .values_list("user_id", flat=True)[:500]
    )


def is_member(user, conversation_id) -> bool:
    return (
        ConversationMember.objects.filter(conversation_id=conversation_id, user=user)
        .exclude(status__in=[Member.Status.LEFT, Member.Status.DECLINED])
        .exists()
    )
