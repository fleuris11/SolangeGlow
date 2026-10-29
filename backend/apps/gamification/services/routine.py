"""« My routine »: beauty steps to tick in the morning and in the evening, with reminders
at the hours she chose (in her time zone)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import translation

from apps.notifications.services import notify

from .. import errors
from ..models import Action, GlowProfile, Moment, RoutineCheck, RoutineStep
from . import points
from .common import local_now, locked_profile, profile_of, require_games, setting, today


def most_steps() -> int:
    return int(setting("games.routine_max_steps", 8))


@transaction.atomic
def save_steps(user, *, morning: list[str], evening: list[str]) -> None:
    """Her steps, in order. A step kept at the same place keeps today's tick."""
    require_games(user)
    most = most_steps()
    for moment, labels in ((Moment.MORNING, morning), (Moment.EVENING, evening)):
        labels = [label.strip()[:60] for label in labels if label and label.strip()]
        if len(labels) > most:
            raise errors.TooManySteps(details={"count": most})
        existing = list(RoutineStep.objects.filter(user=user, moment=moment).order_by("position"))
        for position, label in enumerate(labels):
            if position < len(existing):
                step = existing[position]
                if step.label != label:
                    step.label = label
                    step.save(update_fields=["label", "updated_at"])
                    step.checks.all().delete()
            else:
                RoutineStep.objects.create(user=user, moment=moment, label=label, position=position)
        RoutineStep.objects.filter(pk__in=[s.pk for s in existing[len(labels) :]]).delete()


@transaction.atomic
def set_reminders(
    user,
    *,
    routine_reminders: bool,
    morning_at: datetime.time,
    evening_at: datetime.time,
    celebration_reminders: bool,
) -> GlowProfile:
    profile = locked_profile(user)
    profile.routine_reminders = routine_reminders
    profile.morning_at = morning_at
    profile.evening_at = evening_at
    profile.celebration_reminders = celebration_reminders
    profile.save()
    return profile


def _complete(user, moment: str, day: datetime.date) -> bool:
    steps = RoutineStep.objects.filter(user=user, moment=moment)
    total = steps.count()
    return total > 0 and RoutineCheck.objects.filter(step__in=steps, day=day).count() == total


@transaction.atomic
def check(user, step_id, *, done: bool, now=None) -> dict:
    require_games(user)
    step = RoutineStep.objects.filter(pk=step_id, user=user).first()
    if step is None:
        raise errors.StepNotFound()
    day = today(user, now)
    if done:
        RoutineCheck.objects.get_or_create(step=step, day=day)
        if _complete(user, step.moment, day):
            points.award(
                user,
                Action.ROUTINE,
                key=f"routine:{user.pk}:{day}:{step.moment}",
                source_type="routine",
                source_id=step.moment,
                now=now,
            )
    else:
        RoutineCheck.objects.filter(step=step, day=day).delete()
    return state(user, now=now)


def state(user, *, now=None) -> dict:
    day = today(user, now)
    profile = profile_of(user)
    ticked = set(
        RoutineCheck.objects.filter(step__user=user, day=day).values_list("step_id", flat=True)
    )
    rows = {Moment.MORNING: [], Moment.EVENING: []}
    for step in RoutineStep.objects.filter(user=user).order_by("moment", "position"):
        rows[step.moment].append({"id": step.pk, "label": step.label, "done": step.pk in ticked})
    return {
        "morning": rows[Moment.MORNING],
        "evening": rows[Moment.EVENING],
        "routine_reminders": profile.routine_reminders,
        "morning_at": profile.morning_at,
        "evening_at": profile.evening_at,
        "celebration_reminders": profile.celebration_reminders,
        "max_steps": most_steps(),
    }


def send_reminders(now=None) -> int:
    """Celery Beat every 15 minutes: a reminder at the chosen hour, if not done yet."""
    window = datetime.timedelta(minutes=int(setting("games.routine_window_minutes", 120)))
    sent = 0
    profiles = GlowProfile.objects.filter(
        routine_reminders=True, user__is_active=True
    ).select_related("user__country")
    for profile in profiles.iterator():
        user = profile.user
        local = local_now(user, now)
        day = local.date()
        for moment, at, field in (
            (Moment.MORNING, profile.morning_at, "morning_reminded_on"),
            (Moment.EVENING, profile.evening_at, "evening_reminded_on"),
        ):
            if getattr(profile, field) == day:
                continue
            start = datetime.datetime.combine(day, at, tzinfo=local.tzinfo)
            if not start <= local < start + window:
                continue
            GlowProfile.objects.filter(pk=profile.pk).update(**{field: day})
            has_steps = RoutineStep.objects.filter(user=user, moment=moment).exists()
            if has_steps and not _complete(user, moment, day):
                with translation.override(user.preferred_language or "fr"):
                    label = str(Moment(moment).label).lower()
                notify(user, "glow.routine_reminder", {"moment": label}, link="/routine")
                sent += 1
    return sent
