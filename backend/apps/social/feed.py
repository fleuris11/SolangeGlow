"""The personalised feed: followed people first, then trending in her city, then her country.

Inside each tier, posts are ordered by a simple score whose weights are platform
settings (`social.feed_weights`):

    score = recency · e^(-age / half-life) + interactions · ln(1 + likes + 2·comments + saves)
            + distance · 1 / (1 + km / 10)          (only when her position is known)

Pagination is a keyset cursor (tier, score, id) computed at a fixed moment (« as of »),
so scrolling never shows a post twice nor skips one, even while time passes.
"""

from __future__ import annotations

import base64
import datetime
import json
from dataclasses import dataclass

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import (
    Case,
    ExpressionWrapper,
    F,
    FloatField,
    Func,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Extract, Ln
from django.utils import timezone

from apps.core.selectors import get_setting
from apps.moderation.selectors import blocked_user_ids, hidden_ids

from .models import Follow, Post, Visibility

DEFAULT_WEIGHTS = {"recency": 1.0, "interactions": 0.4, "distance": 0.3, "half_life_hours": 36}


class Exp(Func):
    function = "EXP"
    output_field = FloatField()


@dataclass(frozen=True)
class Cursor:
    as_of: datetime.datetime
    tier: int
    score: float
    id: str

    def encode(self) -> str:
        raw = json.dumps([self.as_of.isoformat(), self.tier, self.score, self.id])
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str | None) -> Cursor | None:
        if not value:
            return None
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
            as_of, tier, score, post_id = json.loads(raw)
            return cls(
                datetime.datetime.fromisoformat(as_of), int(tier), float(score), str(post_id)
            )
        except (ValueError, TypeError, UnicodeDecodeError):
            return None


def live_posts():
    return Post.objects.filter(
        status=Post.Status.PUBLISHED, visibility=Visibility.VISIBLE, deleted_at__isnull=True
    )


def visible_to(viewer, queryset):
    """Removes posts of blocked people and posts or authors she chose to hide."""
    from apps.accounts.models import User

    blocked = blocked_user_ids(viewer)
    hidden_posts = hidden_ids(viewer, Post)
    hidden_authors = hidden_ids(viewer, User)
    if blocked or hidden_authors:
        queryset = queryset.exclude(author_id__in=blocked | hidden_authors)
    if hidden_posts:
        queryset = queryset.exclude(pk__in=hidden_posts)
    return queryset.filter(author__is_active=True)


def feed(viewer=None, *, city: str = "", country: str = "", near: Point | None = None,
         cursor: str | None = None, size: int | None = None):  # fmt: skip
    """One page of the feed and the cursor of the next one."""
    weights = {**DEFAULT_WEIGHTS, **(get_setting("social.feed_weights", default={}) or {})}
    size = size or int(get_setting("social.feed_page_size", default=12))
    window = int(get_setting("social.feed_window_days", default=60))
    position = Cursor.decode(cursor)
    as_of = position.as_of if position else timezone.now()

    signed_in = viewer is not None and viewer.is_authenticated
    if signed_in:
        city = city or viewer.city
        country = country or (viewer.country.code if viewer.country_id else "")
    followed = (
        list(Follow.objects.filter(follower=viewer).values_list("followed_id", flat=True))
        if signed_in
        else []
    )

    posts = visible_to(viewer, live_posts()).filter(
        published_at__lte=as_of, published_at__gte=as_of - datetime.timedelta(days=window)
    )
    if signed_in:
        posts = posts.exclude(author=viewer)

    age_hours = ExpressionWrapper(
        Extract(Value(as_of) - F("published_at"), "epoch") / 3600.0, output_field=FloatField()
    )
    recency = Exp(-age_hours / float(weights["half_life_hours"]))
    interactions = Ln(
        Cast(1 + F("like_count") + 2 * F("comment_count") + F("save_count"), FloatField())
    )
    score = float(weights["recency"]) * recency + float(weights["interactions"]) * interactions
    if near is not None:
        posts = posts.annotate(km=Distance("location", near) / 1000.0)
        closeness = Coalesce(1.0 / (1.0 + F("km") / 10.0), Value(0.0), output_field=FloatField())
        score = score + float(weights["distance"]) * closeness

    tiers = []
    if followed:
        tiers.append(When(author_id__in=followed, then=Value(0)))
    if city:
        tiers.append(When(city__iexact=city, then=Value(1)))
    if country:
        tiers.append(When(country__code=country, then=Value(2)))
    tier = Case(*tiers, default=Value(3), output_field=IntegerField()) if tiers else Value(3)
    posts = posts.annotate(tier=tier, score=ExpressionWrapper(score, output_field=FloatField()))
    if position:
        posts = posts.filter(
            Q(tier__gt=position.tier)
            | Q(tier=position.tier, score__lt=position.score)
            | Q(tier=position.tier, score=position.score, pk__gt=position.id)
        )
    rows = list(
        posts.select_related("author", "pro", "trade", "service")
        .prefetch_related("media_items__media")
        .order_by("tier", "-score", "pk")[: size + 1]
    )
    more = len(rows) > size
    rows = rows[:size]
    next_cursor = (
        Cursor(as_of, rows[-1].tier, rows[-1].score, str(rows[-1].pk)).encode()
        if more and rows
        else None
    )
    return rows, next_cursor
