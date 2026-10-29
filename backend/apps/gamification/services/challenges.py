"""The photo challenge of the week: a theme (« pagne look of Sunday »), photos, votes; the
winner is shown on the home page the week after."""

from __future__ import annotations

import datetime
import logging

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone, translation

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.media.services import variant_url
from apps.core.providers import ProviderError, ProviderNotConfigured
from apps.moderation import selectors as moderation
from apps.moderation.services import screen
from apps.notifications.services import notify
from apps.social.models import Visibility

from .. import errors
from ..generators import generator
from ..models import Action, Challenge, ChallengeEntry, ChallengeVote
from . import points
from .common import require_games, setting, today

logger = logging.getLogger("solangeglow.games")
PURPOSE = "challenge_photo"


def monday_of(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=day.weekday())


def current(day: datetime.date | None = None) -> Challenge | None:
    day = day or timezone.localdate()
    return Challenge.objects.filter(
        status=Challenge.Status.APPROVED, starts_on__lte=day, ends_on__gte=day
    ).first()


def featured(day: datetime.date | None = None) -> Challenge | None:
    """The last challenge won, shown on the home page for a few days."""
    day = day or timezone.localdate()
    days = int(setting("games.winner_featured_days", 7))
    return (
        Challenge.objects.filter(
            status=Challenge.Status.CLOSED,
            winner__isnull=False,
            winner__visibility=Visibility.VISIBLE,
            ends_on__gte=day - datetime.timedelta(days=days),
        )
        .select_related("winner__author", "winner__photo")
        .order_by("-ends_on")
        .first()
    )


def entries(challenge: Challenge, viewer=None):
    rows = challenge.entries.filter(visibility=Visibility.VISIBLE).select_related("author", "photo")
    if viewer is not None:
        rows = rows.exclude(author_id__in=moderation.blocked_user_ids(viewer)).exclude(
            pk__in=moderation.hidden_ids(viewer, ChallengeEntry)
        )
    return rows.order_by("-votes", "created_at")


def votes_left(user, challenge: Challenge) -> int:
    most = int(setting("games.challenge_votes_per_person", 3))
    return max(0, most - ChallengeVote.objects.filter(user=user, challenge=challenge).count())


@transaction.atomic
def enter(user, *, photo_id, caption: str = "", now=None) -> ChallengeEntry:
    require_games(user)
    challenge = current(today(user, now))
    if challenge is None:
        raise errors.NoChallenge()
    if not moderation.can_post(user):
        raise errors.CannotPost()
    photo = MediaAsset.objects.filter(
        pk=photo_id, owner=user, purpose=PURPOSE, kind="image"
    ).first()
    if photo is None or photo.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED):
        raise errors.InvalidPhotos()
    try:
        with transaction.atomic():
            entry = ChallengeEntry.objects.create(
                challenge=challenge, author=user, photo=photo, caption=(caption or "").strip()[:140]
            )
    except IntegrityError as exc:
        raise errors.AlreadyEntered() from exc
    url = variant_url(photo, "medium")
    screen(entry, text=entry.caption, image_urls=[url] if url else [])
    entry.refresh_from_db(fields=["visibility"])
    if entry.visibility == Visibility.VISIBLE:
        points.award(
            user,
            Action.CHALLENGE_ENTRY,
            key=f"challenge_entry:{entry.pk}",
            source_type="challenge",
            source_id=challenge.pk,
            now=now,
        )
    return entry


@transaction.atomic
def vote(user, entry_id, *, now=None) -> ChallengeEntry:
    require_games(user)
    challenge = current(today(user, now))
    entry = (
        ChallengeEntry.objects.select_for_update()
        .filter(pk=entry_id, challenge=challenge, visibility=Visibility.VISIBLE)
        .first()
        if challenge
        else None
    )
    if entry is None:
        raise errors.EntryNotFound()
    if entry.author_id == user.pk:
        raise errors.OwnEntry()
    if votes_left(user, challenge) <= 0:
        raise errors.NoVotesLeft(
            details={"count": int(setting("games.challenge_votes_per_person", 3))}
        )
    try:
        with transaction.atomic():
            ChallengeVote.objects.create(entry=entry, challenge=challenge, user=user)
    except IntegrityError as exc:
        raise errors.AlreadyVoted() from exc
    ChallengeEntry.objects.filter(pk=entry.pk).update(votes=F("votes") + 1)
    entry.refresh_from_db()
    points.award(
        user,
        Action.CHALLENGE_VOTE,
        key=f"challenge_vote:{entry.pk}:{user.pk}",
        source_type="challenge",
        source_id=challenge.pk,
        now=now,
    )
    return entry


def voted_ids(user, challenge: Challenge) -> set:
    if user is None:
        return set()
    return set(
        ChallengeVote.objects.filter(user=user, challenge=challenge).values_list(
            "entry_id", flat=True
        )
    )


@transaction.atomic
def approve(challenge: Challenge, *, actor) -> Challenge:
    if not (challenge.theme or "").strip():
        raise errors.ChallengeIncomplete()
    challenge.status = Challenge.Status.APPROVED
    challenge.save(update_fields=["status", "updated_at"])
    record("glow.challenge_approved", challenge, actor=actor)
    return challenge


def close_due(now=None) -> int:
    """Celery Beat: ended challenges get their winner (most votes, the first one if equal)."""
    day = timezone.localdate(now)
    closed = 0
    due = Challenge.objects.filter(status=Challenge.Status.APPROVED, ends_on__lt=day)
    for challenge in due:
        with transaction.atomic():
            challenge = Challenge.objects.select_for_update().get(pk=challenge.pk)
            if challenge.status != Challenge.Status.APPROVED:
                continue
            winner = (
                challenge.entries.filter(visibility=Visibility.VISIBLE, votes__gt=0)
                .order_by("-votes", "created_at")
                .select_related("author")
                .first()
            )
            challenge.status = Challenge.Status.CLOSED
            challenge.winner = winner
            challenge.closed_at = timezone.now()
            challenge.save(update_fields=["status", "winner", "closed_at", "updated_at"])
            if winner is not None:
                points.award(
                    winner.author,
                    Action.CHALLENGE_WIN,
                    key=f"challenge_win:{challenge.pk}",
                    source_type="challenge",
                    source_id=challenge.pk,
                )
                notify(
                    winner.author,
                    "glow.challenge_won",
                    {"theme": challenge.theme, "votes": winner.votes},
                    link="/defi",
                )
            closed += 1
    return closed


def prepare(*, now=None) -> int:
    """Draft challenges for the coming weeks (theme proposed by the AI, or written by the
    team); nothing goes online before the approval."""
    start = monday_of(timezone.localdate(now))
    weeks = int(setting("games.challenge_weeks_ahead", 4))
    source = generator()
    created = 0
    for offset in range(1, weeks + 1):
        monday = start + datetime.timedelta(weeks=offset)
        if Challenge.objects.filter(starts_on=monday).exists():
            continue
        try:
            proposal = source.theme(monday, "fr")
        except (ProviderError, ProviderNotConfigured) as exc:
            logger.warning("Challenge generator failed: %s", exc)
            proposal = None
        with translation.override("fr"):
            Challenge.objects.create(
                starts_on=monday,
                ends_on=monday + datetime.timedelta(days=6),
                theme=proposal.theme if proposal else "",
                description=proposal.description if proposal else "",
                generated_by=source.name,
            )
        created += 1
    return created
