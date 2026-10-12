from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from .models import Block, Hide, Sanction


def blocked_user_ids(user) -> set:
    """People she blocked and people who blocked her: they do not see each other."""
    if user is None or not user.is_authenticated:
        return set()
    rows = Block.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list(
        "blocker_id", "blocked_id"
    )
    return {other for pair in rows for other in pair if other != user.pk}


def hidden_ids(user, model) -> set:
    if user is None or not user.is_authenticated:
        return set()
    return set(
        Hide.objects.filter(
            user=user, target_type=ContentType.objects.get_for_model(model)
        ).values_list("target_id", flat=True)
    )


def is_blocked_between(user, other) -> bool:
    if user is None or other is None or not getattr(user, "is_authenticated", False):
        return False
    return Block.objects.filter(
        Q(blocker=user, blocked=other) | Q(blocker=other, blocked=user)
    ).exists()


def active_sanction(user) -> Sanction | None:
    now = timezone.now()
    return (
        Sanction.objects.filter(user=user)
        .exclude(level=Sanction.Level.WARNING)
        .filter(Q(until__isnull=True) | Q(until__gt=now))
        .order_by("-created_at")
        .first()
    )


def can_post(user) -> bool:
    """No active « cannot post », suspension or ban."""
    return user.is_active and active_sanction(user) is None
