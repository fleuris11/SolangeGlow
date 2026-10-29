"""« Help me choose »: two photos, the community votes, the result at the end."""

from __future__ import annotations

import datetime

from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Value, When
from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.core.media.services import variant_url
from apps.moderation import selectors as moderation
from apps.moderation.services import screen
from apps.notifications.services import notify
from apps.social.models import Visibility

from .. import errors
from ..models import Action, Poll, PollVote
from . import points
from .common import require_games, setting

PURPOSE = "poll_photo"


def durations() -> list[int]:
    return [int(h) for h in setting("games.poll_durations_hours", [1, 6, 24, 72]) or [24]]


def _photos(author, ids) -> list[MediaAsset]:
    ids = [i for i in ids if i]
    found = {
        a.pk: a
        for a in MediaAsset.objects.filter(pk__in=ids, owner=author, purpose=PURPOSE, kind="image")
    }
    if len(ids) != 2 or len(set(ids)) != 2 or len(found) != 2:
        raise errors.InvalidPhotos()
    if any(
        a.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED) for a in found.values()
    ):
        raise errors.InvalidPhotos()
    return [found[i] for i in ids]


@transaction.atomic
def create(
    author, *, caption: str, photo_a, photo_b, hours: int, label_a: str = "", label_b: str = ""
) -> Poll:
    require_games(author)
    if not moderation.can_post(author):
        raise errors.CannotPost()
    if hours not in durations():
        raise errors.InvalidDuration()
    most = int(setting("games.poll_max_open", 3))
    if open_polls().filter(author=author).count() >= most:
        raise errors.TooManyPolls(details={"count": most})
    first, second = _photos(author, [photo_a, photo_b])
    poll = Poll.objects.create(
        author=author,
        caption=(caption or "").strip()[:140],
        photo_a=first,
        photo_b=second,
        label_a=(label_a or "").strip()[:40],
        label_b=(label_b or "").strip()[:40],
        ends_at=timezone.now() + datetime.timedelta(hours=hours),
        city=(author.city or "")[:80],
    )
    images = [u for u in (variant_url(first, "medium"), variant_url(second, "medium")) if u]
    screen(poll, text=" ".join([poll.caption, poll.label_a, poll.label_b]), image_urls=images)
    poll.refresh_from_db(fields=["visibility"])
    if poll.visibility == Visibility.VISIBLE:
        points.award(
            author, Action.POLL, key=f"poll:{poll.pk}", source_type="poll", source_id=poll.pk
        )
    return poll


def open_polls():
    return Poll.objects.filter(
        deleted_at__isnull=True, visibility=Visibility.VISIBLE, ends_at__gt=timezone.now()
    )


def visible_to(viewer):
    rows = Poll.objects.filter(deleted_at__isnull=True, visibility=Visibility.VISIBLE)
    if viewer is not None:
        rows = rows.exclude(author_id__in=moderation.blocked_user_ids(viewer)).exclude(
            pk__in=moderation.hidden_ids(viewer, Poll)
        )
    return rows.select_related("author", "photo_a", "photo_b")


def to_vote(viewer):
    """Open polls of others she has not voted on yet, her city first."""
    rows = visible_to(viewer).filter(ends_at__gt=timezone.now())
    if viewer is not None:
        rows = rows.exclude(author=viewer).exclude(votes__user=viewer)
        city = viewer.city or ""
        if city:
            here = Case(
                When(city=city, then=Value(1)), default=Value(0), output_field=IntegerField()
            )
            return rows.annotate(here=here).order_by("-here", "ends_at")
    return rows.order_by("ends_at")


def find(poll_id, viewer=None) -> Poll:
    poll = visible_to(viewer).filter(pk=poll_id).first()
    if poll is None and viewer is not None:
        poll = Poll.objects.filter(pk=poll_id, author=viewer, deleted_at__isnull=True).first()
    if poll is None:
        raise errors.PollNotFound()
    return poll


@transaction.atomic
def vote(user, poll: Poll, choice: str) -> Poll:
    require_games(user)
    if choice not in PollVote.Choice.values:
        raise errors.InvalidChoice()
    poll = Poll.objects.select_for_update().get(pk=poll.pk)
    if poll.author_id == user.pk:
        raise errors.OwnPoll()
    if poll.ends_at <= timezone.now() or poll.visibility != Visibility.VISIBLE:
        raise errors.PollClosed()
    try:
        with transaction.atomic():
            PollVote.objects.create(poll=poll, user=user, choice=choice)
    except IntegrityError as exc:
        raise errors.AlreadyVoted() from exc
    field = "votes_a" if choice == PollVote.Choice.A else "votes_b"
    Poll.objects.filter(pk=poll.pk).update(**{field: F(field) + 1})
    poll.refresh_from_db()
    points.award(
        user,
        Action.POLL_VOTE,
        key=f"poll_vote:{poll.pk}:{user.pk}",
        source_type="poll",
        source_id=poll.pk,
    )
    return poll


def delete(user, poll: Poll) -> None:
    if poll.author_id != user.pk:
        raise errors.PollNotFound()
    Poll.objects.filter(pk=poll.pk).update(deleted_at=timezone.now())


def my_vote(user, poll: Poll) -> str | None:
    if user is None:
        return None
    return PollVote.objects.filter(poll=poll, user=user).values_list("choice", flat=True).first()


def result(poll: Poll) -> dict:
    total = poll.votes_a + poll.votes_b
    share_a = round(poll.votes_a * 100 / total) if total else 0
    return {"total": total, "a": share_a, "b": 100 - share_a if total else 0}


def send_results(now=None) -> int:
    """Celery Beat: the author learns the result when her vote ends."""
    now = now or timezone.now()
    ended = Poll.objects.filter(
        ends_at__lte=now, result_sent_at__isnull=True, deleted_at__isnull=True
    ).select_related("author")
    sent = 0
    for poll in ended:
        if Poll.objects.filter(pk=poll.pk, result_sent_at__isnull=True).update(result_sent_at=now):
            share = result(poll)
            notify(
                poll.author,
                "glow.poll_result",
                {"a": share["a"], "b": share["b"], "total": share["total"]},
                link=f"/choisir/{poll.pk}",
            )
            sent += 1
    return sent
