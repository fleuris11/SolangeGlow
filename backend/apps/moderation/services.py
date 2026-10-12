"""Reports, blocks, hidden contents, automatic checks, decisions and graduated sanctions."""

from __future__ import annotations

import datetime

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from . import errors, providers
from .models import Block, Hide, ModerationCase, Report, Sanction
from .selectors import active_sanction

VISIBLE, HELD, REMOVED = "visible", "held", "removed"

DEFAULT_LADDER = [
    {"level": "warning"},
    {"level": "mute", "days": 3},
    {"level": "suspension", "days": 7},
    {"level": "ban"},
]


# --- What a content is -----------------------------------------------------------------


def author_of(target):
    if getattr(target, "_meta", None) and target._meta.label == "accounts.User":
        return target
    return getattr(target, "author", None)


def excerpt_of(target) -> str:
    for field in ("caption", "text"):
        value = getattr(target, field, None)
        if value:
            return str(value)[:500]
    return str(target)[:500]


def set_visibility(target, value: str) -> None:
    if hasattr(target, "visibility"):
        type(target).objects.filter(pk=target.pk).update(visibility=value)
        target.visibility = value
        on_change = getattr(target, "on_visibility_change", None)
        if on_change:
            on_change()


def _case_for(target, *, source: str) -> ModerationCase:
    target_type = ContentType.objects.get_for_model(target)
    case = ModerationCase.objects.filter(
        target_type=target_type, target_id=target.pk, status=ModerationCase.Status.PENDING
    ).first()
    if case is None:
        author = author_of(target)
        case = ModerationCase.objects.create(
            target_type=target_type,
            target_id=target.pk,
            source=source,
            author=author,
            excerpt=excerpt_of(target),
        )
    return case


# --- Automatic check ---------------------------------------------------------------------


def screen(target, *, text: str = "", image_urls: list[str] | None = None, language="fr"):
    """Checks a new content. Blocked: hidden until a person reviews it. Doubtful: queued.

    Returns the verdict; the caller has already saved the content.
    """
    verdict = providers.check(text=text, image_urls=image_urls, language=language)
    if verdict.action == providers.ALLOW:
        return verdict
    with transaction.atomic():
        case = _case_for(target, source=ModerationCase.Source.AUTOMATIC)
        case.labels = sorted({*case.labels, *verdict.labels})
        case.provider = verdict.provider
        if verdict.action == providers.BLOCK:
            case.hidden_until_review = True
            set_visibility(target, HELD)
        case.save()
    return verdict


# --- Reports, blocks, hides --------------------------------------------------------------


@transaction.atomic
def report(reporter, target, *, reason: str, comment: str = "") -> Report:
    if author_of(target) == reporter:
        raise errors.CannotReportYourself()
    case = _case_for(target, source=ModerationCase.Source.REPORT)
    try:
        with transaction.atomic():
            created = Report.objects.create(
                reporter=reporter,
                target_type=case.target_type,
                target_id=target.pk,
                reason=reason,
                comment=comment.strip()[:500],
                case=case,
            )
    except IntegrityError as exc:
        raise errors.AlreadyReported() from exc
    case.report_count = case.reports.count()
    threshold = int(get_setting("moderation.auto_hide_reports", default=3))
    if case.report_count >= threshold and not case.hidden_until_review:
        case.hidden_until_review = True
        set_visibility(target, HELD)
    case.save()
    return created


def block(user, other) -> Block:
    if user.pk == other.pk:
        raise errors.CannotBlockYourself()
    from apps.social.models import Follow

    with transaction.atomic():
        item, _ = Block.objects.get_or_create(blocker=user, blocked=other)
        # Blocking ends the follow in both directions.
        Follow.objects.filter(follower=user, followed=other).delete()
        Follow.objects.filter(follower=other, followed=user).delete()
    return item


def unblock(user, other) -> None:
    Block.objects.filter(blocker=user, blocked=other).delete()


def hide(user, target) -> Hide:
    item, _ = Hide.objects.get_or_create(
        user=user, target_type=ContentType.objects.get_for_model(target), target_id=target.pk
    )
    return item


def unhide(user, target) -> None:
    Hide.objects.filter(
        user=user, target_type=ContentType.objects.get_for_model(target), target_id=target.pk
    ).delete()


# --- Decisions of the team ----------------------------------------------------------------


@transaction.atomic
def decide(case: ModerationCase, *, actor, keep: bool, sanction: bool = False, note: str = ""):
    """One click in the queue: keep the content, or remove it (and sanction the author)."""
    target = case.target
    case.status = ModerationCase.Status.KEPT if keep else ModerationCase.Status.REMOVED
    case.decided_by = actor
    case.decided_at = timezone.now()
    case.note = note
    case.save()
    if target is not None:
        if keep:
            set_visibility(target, VISIBLE)
        else:
            set_visibility(target, REMOVED)
            author = author_of(target)
            if author is not None and author != target:
                notify(author, "moderation.content_removed", {"excerpt": case.excerpt[:80]})
            if sanction and author is not None:
                apply_sanction(author, actor=actor, case=case, reason=note)
    record(
        "moderation.kept" if keep else "moderation.removed",
        case,
        actor=actor,
        metadata={"sanction": sanction, "note": note},
    )
    return case


def next_level(user) -> dict:
    ladder = get_setting("moderation.sanction_ladder", default=DEFAULT_LADDER) or DEFAULT_LADDER
    window = int(get_setting("moderation.sanction_window_days", default=180))
    since = timezone.now() - datetime.timedelta(days=window)
    previous = Sanction.objects.filter(user=user, created_at__gte=since).count()
    return ladder[min(previous, len(ladder) - 1)]


@transaction.atomic
def apply_sanction(user, *, actor, case=None, reason: str = "", level: str | None = None):
    """The next step of the ladder (warning, cannot post, suspension, ban), or a chosen one."""
    step = {"level": level} if level else next_level(user)
    days = step.get("days")
    until = timezone.now() + datetime.timedelta(days=int(days)) if days else None
    sanction = Sanction.objects.create(
        user=user,
        level=step["level"],
        until=until,
        reason=reason,
        case=case,
        decided_by=actor,
    )
    if sanction.level in (Sanction.Level.SUSPENSION, Sanction.Level.BAN):
        from apps.accounts.services import suspend

        suspend(user, actor=actor)
    record("moderation.sanction", user, actor=actor, metadata={"level": sanction.level})
    notify(
        user,
        "moderation.sanction",
        {"level": str(sanction.get_level_display()), "until": until.date() if until else ""},
    )
    return sanction


def lift_expired_sanctions() -> int:
    """Celery Beat: a suspension that has ended gives the account back."""
    from apps.accounts.models import User
    from apps.accounts.services import reactivate

    now = timezone.now()
    ended = Sanction.objects.filter(level=Sanction.Level.SUSPENSION, until__lte=now)
    count = 0
    for user in User.objects.filter(sanctions__in=ended, is_active=False).distinct():
        if active_sanction(user) is None and not user.deleted_at:
            reactivate(user, actor=None)
            count += 1
    return count
