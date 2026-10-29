"""The streak of visits: one visit a day, a bonus every N days in a row; the flame goes
out when a day is missed."""

from __future__ import annotations

import datetime

from django.db import transaction

from ..models import Action, GlowProfile
from . import points
from .common import locked_profile, profile_of, require_games, setting, today


def bonus_every() -> int:
    return max(1, int(setting("glow.streak_bonus_every", 7)))


def current(profile: GlowProfile, day: datetime.date) -> int:
    """Days in a row still alive today (visited today or yesterday), else 0."""
    if profile.last_checkin_on is None:
        return 0
    if (day - profile.last_checkin_on).days <= 1:
        return profile.streak
    return 0


def check_in(user, *, now=None) -> dict:
    """Today's visit: the points of the day once, the bonus at the end of each series."""
    require_games(user)
    day = today(user, now)
    gained = bonus = 0
    with transaction.atomic():
        profile = locked_profile(user)
        already = profile.last_checkin_on == day
        if not already:
            yesterday = day - datetime.timedelta(days=1)
            profile.streak = profile.streak + 1 if profile.last_checkin_on == yesterday else 1
            profile.best_streak = max(profile.best_streak, profile.streak)
            profile.last_checkin_on = day
            profile.save(update_fields=["streak", "best_streak", "last_checkin_on", "updated_at"])
    if not already:
        entry = points.award(user, Action.CHECKIN, key=f"checkin:{user.pk}:{day}", now=now)
        gained = entry.amount if entry else 0
        if profile.streak % bonus_every() == 0:
            entry = points.award(user, Action.STREAK, key=f"streak:{user.pk}:{day}", now=now)
            bonus = entry.amount if entry else 0
    return {**state(user, now=now), "already": already, "gained": gained, "bonus": bonus}


def state(user, *, now=None) -> dict:
    profile = profile_of(user)
    day = today(user, now)
    alive = current(profile, day)
    every = bonus_every()
    return {
        "streak": alive,
        "best": profile.best_streak,
        "today_done": profile.last_checkin_on == day,
        "bonus_every": every,
        # Days still needed for the next bonus.
        "to_bonus": every - (alive % every),
    }
