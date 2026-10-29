"""Glow Points: the scale per action, the anti-abuse caps, the levels, spending.

Every movement is a ``PointsEntry`` written once under a unique key (a replayed event
gives nothing more); the balance is the sum of the entries.
"""

from __future__ import annotations

import math
import uuid

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum

from apps.core.audit.services import record
from apps.notifications.services import notify

from .. import errors
from ..models import LEVEL_ORDER, Action, Level, PointsEntry
from .common import games_on, locked_profile, profile_of, setting, today

DEFAULT_SCALE = {
    Action.CHECKIN: 5,
    Action.STREAK: 50,
    Action.POST: 10,
    Action.REVIEW: 20,
    Action.BOOKING: 30,
    Action.PURCHASE: 30,
    Action.REFERRAL: 200,
    Action.REFERRED: 100,
    Action.QUIZ: 10,
    Action.POLL: 5,
    Action.POLL_VOTE: 2,
    Action.CHALLENGE_ENTRY: 15,
    Action.CHALLENGE_VOTE: 2,
    Action.CHALLENGE_WIN: 300,
    Action.ROUTINE: 3,
}
DEFAULT_CAPS = {
    Action.POST: 3,
    Action.REVIEW: 5,
    Action.BOOKING: 3,
    Action.PURCHASE: 5,
    Action.POLL: 2,
    Action.POLL_VOTE: 20,
    Action.CHALLENGE_VOTE: 10,
    Action.ROUTINE: 2,
}
# Defaults while the setting is missing; once written in the admin, the setting is the rule.
# Bonuses that are not counted in the daily ceiling (and get no level multiplier).
DEFAULT_UNCAPPED = [
    Action.STREAK,
    Action.REFERRAL,
    Action.REFERRED,
    Action.CHALLENGE_WIN,
    Action.WHEEL,
]
DEFAULT_THRESHOLDS = {Level.STAR: 1000, Level.ICON: 5000}
DEFAULT_MULTIPLIERS = {Level.GLOW: 1, Level.STAR: 1.1, Level.ICON: 1.25}


def scale() -> dict:
    return dict(setting("glow.points", DEFAULT_SCALE) or {})


def caps() -> dict:
    return dict(setting("glow.daily_caps", DEFAULT_CAPS) or {})


def uncapped() -> set:
    return set(setting("glow.uncapped_actions", DEFAULT_UNCAPPED) or [])


def thresholds() -> dict:
    return dict(setting("glow.level_thresholds", DEFAULT_THRESHOLDS) or {})


def multiplier(level: str) -> float:
    values = setting("glow.level_multipliers", DEFAULT_MULTIPLIERS) or {}
    return float(values.get(level, 1))


def level_for(earned: int) -> str:
    reached = Level.GLOW
    limits = thresholds()
    for level in LEVEL_ORDER[1:]:
        if earned >= int(limits.get(level, 10**9)):
            reached = level
    return reached


def next_level(earned: int) -> tuple[str | None, int | None]:
    """The next level and the points earned it needs, or (None, None) at the top."""
    limits = thresholds()
    for level in LEVEL_ORDER[1:]:
        needed = int(limits.get(level, 10**9))
        if earned < needed:
            return level, needed
    return None, None


def balance(user) -> int:
    return PointsEntry.objects.filter(user=user).aggregate(total=Sum("amount"))["total"] or 0


def earned_on(user, day) -> dict:
    """Gains of a day: count per action and the points that count in the ceiling."""
    rows = PointsEntry.objects.filter(user=user, day=day, amount__gt=0)
    counts = dict(rows.values_list("action").annotate(n=Count("id")).values_list("action", "n"))
    ceiling = rows.exclude(action__in=uncapped()).aggregate(total=Sum("amount"))["total"] or 0
    return {"counts": counts, "ceiling": ceiling}


def _write(profile, *, amount: int, action: str, key: str, day, **extra) -> PointsEntry | None:
    try:
        with transaction.atomic():
            return PointsEntry.objects.create(
                user=profile.user, amount=amount, action=action, key=key[:120], day=day, **extra
            )
    except IntegrityError:
        return None  # already written under this key: an event replayed gives nothing more


def _raise_level(profile) -> None:
    level = level_for(profile.earned_total)
    if LEVEL_ORDER.index(level) > LEVEL_ORDER.index(profile.level):
        profile.level = level
        notify(profile.user, "glow.level_up", {"level": Level(level).label}, link="/points")


def award(
    user,
    action: str,
    *,
    key: str,
    points: int | None = None,
    source_type: str = "",
    source_id="",
    now=None,
) -> PointsEntry | None:
    """Gives the points of an action, within the caps of the day. None when nothing is
    given (games closed, cap reached, already given under this key)."""
    if user is None or not getattr(user, "is_active", False) or not games_on(user):
        return None
    base = int(points if points is not None else scale().get(action, 0) or 0)
    if base <= 0:
        return None
    with transaction.atomic():
        profile = locked_profile(user)
        if PointsEntry.objects.filter(key=key[:120]).exists():
            return None
        day = today(user, now)
        done = earned_on(user, day)
        limit = caps().get(action)
        if limit is not None and done["counts"].get(action, 0) >= int(limit):
            return None
        amount = base
        if action not in uncapped():
            amount = math.floor(base * multiplier(profile.level))
            room = int(setting("glow.daily_max_points", 400)) - done["ceiling"]
            amount = min(amount, room)
            if amount <= 0:
                return None
        entry = _write(
            profile,
            amount=amount,
            action=action,
            key=key,
            day=day,
            source_type=source_type,
            source_id=str(source_id or ""),
        )
        if entry is None:
            return None
        profile.earned_total += amount
        _raise_level(profile)
        profile.save(update_fields=["earned_total", "level", "updated_at"])
    return entry


def spend(
    user, cost: int, *, key: str, source_type: str = "", source_id="", note: str = ""
) -> PointsEntry:
    """Takes points for a reward (inside the caller's transaction)."""
    profile = locked_profile(user)
    left = balance(user)
    if cost > left:
        raise errors.NotEnoughPoints(details={"balance": left, "cost": cost})
    entry = _write(
        profile,
        amount=-cost,
        action=Action.REWARD,
        key=key,
        day=today(user),
        source_type=source_type,
        source_id=str(source_id or ""),
        note=note[:200],
    )
    if entry is None:
        raise errors.NotEnoughPoints(details={"balance": left, "cost": cost})
    return entry


@transaction.atomic
def adjust(user, amount: int, *, note: str, actor) -> PointsEntry:
    """A correction by the team (a gift of points, a fraud taken back), never below zero."""
    profile = locked_profile(user)
    left = balance(user)
    if amount == 0 or left + amount < 0:
        raise errors.NotEnoughPoints(details={"balance": left, "cost": -amount})
    entry = PointsEntry.objects.create(
        user=user,
        amount=amount,
        action=Action.ADJUSTMENT,
        key=f"adjust:{uuid.uuid4()}",
        day=today(user),
        note=note[:200],
        actor=actor,
    )
    if amount > 0:
        profile.earned_total += amount
        _raise_level(profile)
        profile.save(update_fields=["earned_total", "level", "updated_at"])
    record("glow.points_adjusted", entry, actor=actor, after={"amount": amount, "note": note})
    return entry


def summary(user) -> dict:
    profile = profile_of(user)
    upcoming, needed = next_level(profile.earned_total)
    return {
        "balance": balance(user),
        "earned_total": profile.earned_total,
        "level": profile.level,
        "next_level": upcoming,
        "next_level_at": needed,
        "multiplier": multiplier(profile.level),
    }


def history(user, limit: int = 50):
    return PointsEntry.objects.filter(user=user).order_by("-created_at")[:limit]
