"""Business rules of the social network: posts, interactions, follows, stories, reviews."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F
from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.core.media.services import variant_url
from apps.core.selectors import get_setting
from apps.moderation import errors as moderation_errors
from apps.moderation import selectors as moderation
from apps.moderation.services import screen
from apps.notifications.services import notify
from apps.pros.models import ProProfile, Service, Trade

from . import eligibility, errors, products
from .models import (
    ClientRating,
    Comment,
    Follow,
    Like,
    Post,
    PostMedia,
    Review,
    SavedPost,
    Share,
    Story,
    StoryView,
    Visibility,
)

SLOT = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _setting(key: str, default):
    return get_setting(key, default=default)


def _ensure_can_post(user) -> None:
    if not moderation.can_post(user):
        raise moderation_errors.Restricted()


def _pro_of(user) -> ProProfile | None:
    """Her showcase, when she posts as a pro."""
    return ProProfile.objects.filter(user=user).select_related("country").first()


def _place_of(user, pro: ProProfile | None) -> dict:
    if pro is not None and pro.city:
        return {"city": pro.city, "country": pro.country, "location": pro.location}
    return {"city": user.city, "country": user.country, "location": None}


def _language(user) -> str:
    return getattr(user, "preferred_language", "fr") or "fr"


# --- Posts -----------------------------------------------------------------------------


MEDIA_RULES = {
    Post.Kind.PHOTO: "one picture",
    Post.Kind.VIDEO: "one video",
    Post.Kind.CAROUSEL: "2 pictures or videos or more",
    Post.Kind.BEFORE_AFTER: "a « before » and an « after » picture",
}


def _check_media(author, kind: str, items: list[dict]) -> list[tuple[MediaAsset, str]]:
    ids = [item["id"] for item in items]
    assets = {a.pk: a for a in MediaAsset.objects.filter(pk__in=ids, owner=author, purpose="post")}
    if len(assets) != len(set(ids)):
        raise errors.InvalidMedia(errors.InvalidMedia.message % {"rule": MEDIA_RULES[kind]})
    chosen = [(assets[item["id"]], item.get("role") or PostMedia.Role.ITEM) for item in items]
    if any(a.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED) for a, _ in chosen):
        raise errors.MediaNotReady()
    kinds = [a.kind for a, _ in chosen]
    roles = [role for _, role in chosen]
    maximum = int(_setting("social.carousel_max", 10))
    ok = {
        Post.Kind.PHOTO: kinds == ["image"],
        Post.Kind.VIDEO: kinds == ["video"],
        Post.Kind.CAROUSEL: 2 <= len(kinds) <= maximum,
        Post.Kind.BEFORE_AFTER: sorted(roles) == ["after", "before"] and set(kinds) == {"image"},
    }[kind]
    if not ok:
        raise errors.InvalidMedia(errors.InvalidMedia.message % {"rule": MEDIA_RULES[kind]})
    return chosen


def _schedule(status: str, publish_at: datetime.datetime | None) -> dict:
    now = timezone.now()
    if status == Post.Status.PUBLISHED:
        return {"status": status, "publish_at": None, "published_at": now}
    if status == Post.Status.SCHEDULED:
        days = int(_setting("social.schedule_max_days", 30))
        if (
            publish_at is None
            or publish_at <= now
            or publish_at > now + datetime.timedelta(days=days)
        ):
            raise errors.InvalidSchedule(errors.InvalidSchedule.message % {"days": days})
        return {"status": status, "publish_at": publish_at, "published_at": None}
    return {"status": Post.Status.DRAFT, "publish_at": None, "published_at": None}


def _image_urls(post: Post) -> list[str]:
    urls = []
    for item in post.media_items.select_related("media"):
        url = variant_url(item.media, "medium") or variant_url(item.media, "poster_medium")
        if url:
            urls.append(url)
    return urls


@transaction.atomic
def create_post(
    author,
    *,
    kind: str,
    media: list[dict],
    caption: str = "",
    trade_key: str | None = None,
    service_id=None,
    product_id=None,
    status: str = Post.Status.PUBLISHED,
    publish_at: datetime.datetime | None = None,
) -> Post:
    _ensure_can_post(author)
    if not media:
        raise errors.EmptyPost()
    chosen = _check_media(author, kind, media)
    pro = _pro_of(author)
    service = None
    if service_id:
        service = Service.objects.filter(
            pk=service_id, pro__user=author, archived_at__isnull=True
        ).first()
        if service is None:
            raise errors.InvalidLink()
    if product_id and not products.owns(author, product_id):
        raise errors.InvalidLink()
    trade = Trade.objects.filter(key=trade_key, is_active=True).first() if trade_key else None
    if trade is None and service is not None:
        trade = service.trade
    post = Post.objects.create(
        author=author,
        pro=pro,
        kind=kind,
        caption=caption.strip(),
        trade=trade,
        service=service,
        product_id=product_id,
        **_place_of(author, pro),
        **_schedule(status, publish_at),
    )
    PostMedia.objects.bulk_create(
        PostMedia(post=post, media=asset, role=role, position=index)
        for index, (asset, role) in enumerate(chosen)
    )
    screen(post, text=post.caption, image_urls=_image_urls(post), language=_language(author))
    return post


@transaction.atomic
def update_post(post: Post, actor, **changes) -> Post:
    if post.author_id != actor.pk:
        raise errors.NotYours()
    if "caption" in changes:
        post.caption = (changes["caption"] or "").strip()
    if "trade_key" in changes:
        key = changes["trade_key"]
        post.trade = Trade.objects.filter(key=key, is_active=True).first() if key else None
    if "service_id" in changes:
        service_id = changes["service_id"]
        post.service = (
            Service.objects.filter(pk=service_id, pro__user=actor).first() if service_id else None
        )
        if service_id and post.service is None:
            raise errors.InvalidLink()
    if "product_id" in changes:
        product_id = changes["product_id"]
        if product_id and not products.owns(actor, product_id):
            raise errors.InvalidLink()
        post.product_id = product_id
    if "status" in changes and post.status != Post.Status.PUBLISHED:
        _ensure_can_post(actor)
        for field, value in _schedule(changes["status"], changes.get("publish_at")).items():
            setattr(post, field, value)
    post.save()
    if "caption" in changes:
        screen(post, text=post.caption, language=_language(actor))
    return post


def delete_post(post: Post, actor) -> None:
    if post.author_id != actor.pk and not actor.is_staff:
        raise errors.NotYours()
    post.deleted_at = timezone.now()
    post.save(update_fields=["deleted_at", "updated_at"])


def publish_due_posts() -> int:
    """Celery Beat: scheduled posts whose time has come go online."""
    now = timezone.now()
    due = list(Post.objects.filter(status=Post.Status.SCHEDULED, publish_at__lte=now))
    for post in due:
        Post.objects.filter(pk=post.pk).update(
            status=Post.Status.PUBLISHED, published_at=post.publish_at
        )
        notify(post.author, "social.post_published", link=f"/p/{post.pk}")
    return len(due)


def live_post(post_id, viewer=None) -> Post:
    post = Post.objects.select_related("author").filter(pk=post_id, deleted_at__isnull=True).first()
    if post is None:
        raise errors.PostNotFound()
    is_author = viewer is not None and viewer.is_authenticated and viewer.pk == post.author_id
    if not post.is_live and not is_author:
        raise errors.PostNotFound()
    if viewer is not None and moderation.is_blocked_between(viewer, post.author):
        raise errors.PostNotFound()
    return post


# --- Likes, saves, shares --------------------------------------------------------------


def like(user, post: Post) -> Post:
    try:
        with transaction.atomic():
            Like.objects.create(user=user, post=post)
            Post.objects.filter(pk=post.pk).update(like_count=F("like_count") + 1)
    except IntegrityError:
        pass  # already liked
    post.refresh_from_db(fields=["like_count"])
    return post


def unlike(user, post: Post) -> Post:
    if Like.objects.filter(user=user, post=post).delete()[0]:
        Post.objects.filter(pk=post.pk, like_count__gt=0).update(like_count=F("like_count") - 1)
    post.refresh_from_db(fields=["like_count"])
    return post


def save(user, post: Post) -> Post:
    try:
        with transaction.atomic():
            SavedPost.objects.create(user=user, post=post)
            Post.objects.filter(pk=post.pk).update(save_count=F("save_count") + 1)
    except IntegrityError:
        pass
    post.refresh_from_db(fields=["save_count"])
    return post


def unsave(user, post: Post) -> Post:
    if SavedPost.objects.filter(user=user, post=post).delete()[0]:
        Post.objects.filter(pk=post.pk, save_count__gt=0).update(save_count=F("save_count") - 1)
    post.refresh_from_db(fields=["save_count"])
    return post


def record_share(user, post: Post, network: str) -> None:
    Share.objects.create(
        user=user if user is not None and user.is_authenticated else None,
        post=post,
        network=network if network in Share.Network.values else Share.Network.OTHER,
    )
    Post.objects.filter(pk=post.pk).update(share_count=F("share_count") + 1)


# --- Comments ----------------------------------------------------------------------------


def recount_comments(post_id) -> None:
    visible = Comment.objects.filter(
        post_id=post_id, deleted_at__isnull=True, visibility=Visibility.VISIBLE
    ).count()
    Post.objects.filter(pk=post_id).update(comment_count=visible)


@transaction.atomic
def comment(author, post: Post, text: str, *, parent_id=None) -> Comment:
    _ensure_can_post(author)
    if not post.is_live:
        raise errors.PostNotFound()
    if moderation.is_blocked_between(author, post.author):
        raise errors.Blocked()
    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id, post=post, deleted_at__isnull=True).first()
        if parent is None:
            raise errors.CommentNotFound()
        if moderation.is_blocked_between(author, parent.author):
            raise errors.Blocked()
        parent = parent.parent or parent  # one level of replies
    text = text.strip()
    created = Comment.objects.create(post=post, author=author, parent=parent, text=text)
    screen(created, text=text, language=_language(author))
    recount_comments(post.pk)
    created.refresh_from_db()
    if created.visibility == Visibility.VISIBLE:
        context = {"name": author.first_name or "?", "text": text[:80]}
        if parent is not None and parent.author_id != author.pk:
            notify(parent.author, "social.reply", context, link=f"/p/{post.pk}")
        if post.author_id != author.pk and (parent is None or parent.author_id != post.author_id):
            notify(post.author, "social.comment", context, link=f"/p/{post.pk}")
    return created


def delete_comment(item: Comment, actor) -> None:
    if actor.pk not in (item.author_id, item.post.author_id) and not actor.is_staff:
        raise errors.NotYours()
    item.deleted_at = timezone.now()
    item.save(update_fields=["deleted_at", "updated_at"])
    recount_comments(item.post_id)


# --- Follows -------------------------------------------------------------------------------


def follow(follower, followed) -> Follow:
    if follower.pk == followed.pk:
        raise errors.CannotFollowYourself()
    if moderation.is_blocked_between(follower, followed):
        raise errors.Blocked()
    item, created = Follow.objects.get_or_create(follower=follower, followed=followed)
    if created:
        notify(
            followed,
            "social.new_follower",
            {"name": follower.first_name or "?"},
            link="/following",
        )
    return item


def unfollow(follower, followed) -> None:
    Follow.objects.filter(follower=follower, followed=followed).delete()


# --- Stories -------------------------------------------------------------------------------


@transaction.atomic
def create_story(
    author,
    *,
    kind: str,
    media_id=None,
    text: str = "",
    background: str = Story.Background.HIBISCUS,
    slots: list[str] | None = None,
) -> Story:
    _ensure_can_post(author)
    pro = _pro_of(author)
    media = None
    text = (text or "").strip()[:200]
    if kind in (Story.Kind.PHOTO, Story.Kind.VIDEO):
        wanted = "image" if kind == Story.Kind.PHOTO else "video"
        media = MediaAsset.objects.filter(
            pk=media_id, owner=author, purpose="story", kind=wanted
        ).first()
        if media is None:
            raise errors.InvalidStory()
    elif kind == Story.Kind.TEXT:
        if not text:
            raise errors.InvalidStory()
    elif kind == Story.Kind.FREE_SLOTS:
        if pro is None:
            raise errors.NotAPro()
        slots = sorted(set(slots or []))
        if not slots or not all(SLOT.match(s) for s in slots) or len(slots) > 24:
            raise errors.InvalidSlots()
    else:
        raise errors.InvalidStory()
    hours = int(_setting("social.story_hours", 24))
    place = _place_of(author, pro)
    story = Story.objects.create(
        author=author,
        pro=pro,
        kind=kind,
        media=media,
        text=text,
        background=background if background in Story.Background.values else "hibiscus",
        slots=slots if kind == Story.Kind.FREE_SLOTS else [],
        expires_at=timezone.now() + datetime.timedelta(hours=hours),
        city=place["city"],
        country=place["country"],
    )
    screen(story, text=text, language=_language(author))
    return story


def delete_story(story: Story, actor) -> None:
    if story.author_id != actor.pk and not actor.is_staff:
        raise errors.NotYours()
    story.delete()


def mark_seen(story: Story, user) -> None:
    StoryView.objects.get_or_create(story=story, user=user)


# --- Reviews and client ratings ------------------------------------------------------------


def _transaction(kind: str, transaction_id):
    provider = eligibility.provider_for(kind)
    found = provider.get(transaction_id) if provider else None
    if found is None:
        raise errors.TransactionNotFound()
    return found


def check_review_eligibility(user, kind: str, transaction_id) -> eligibility.Transaction:
    """The rules of a verified review, in order. Raises the first one that fails."""
    found = _transaction(kind, transaction_id)
    if found.client_id != user.pk:
        raise errors.NotYourTransaction()
    if found.finished_at is None or found.finished_at > timezone.now():
        raise errors.NotFinished()
    days = int(_setting("reviews.window_days", 30))
    if timezone.now() - found.finished_at > datetime.timedelta(days=days):
        raise errors.TooLate(errors.TooLate.message % {"days": days})
    if Review.objects.filter(source_type=kind, source_id=found.id).exists():
        raise errors.AlreadyReviewed()
    if ProProfile.objects.filter(pk=found.pro_id, user=user).exists():
        raise errors.NotYourTransaction()
    return found


def pending_reviews(user) -> list[eligibility.Transaction]:
    """Finished bookings and orders she can still review."""
    days = int(_setting("reviews.window_days", 30))
    since = timezone.now() - datetime.timedelta(days=days)
    reviewed = set(Review.objects.filter(author=user).values_list("source_id", flat=True))
    pending = []
    for provider in eligibility.all_providers():
        for found in provider.finished_for_client(user.pk):
            finished = found.finished_at
            if finished and since <= finished <= timezone.now() and found.id not in reviewed:
                pending.append(found)
    return sorted(pending, key=lambda t: t.finished_at, reverse=True)


def recompute_rating(pro_id) -> None:
    stats = Review.objects.filter(pro_id=pro_id, visibility=Visibility.VISIBLE).aggregate(
        average=Avg("rating"), count=Count("pk")
    )
    average = stats["average"]
    ProProfile.objects.filter(pk=pro_id).update(
        rating_average=Decimal(str(round(average, 2))) if average is not None else None,
        rating_count=stats["count"],
    )


def _review_media(author, media_id, purpose: str) -> MediaAsset | None:
    if not media_id:
        return None
    asset = MediaAsset.objects.filter(pk=media_id, owner=author, purpose=purpose).first()
    if asset is None:
        raise errors.MediaNotReady()
    return asset


@transaction.atomic
def create_review(
    author,
    *,
    kind: str,
    transaction_id,
    rating: int,
    text: str = "",
    photo_id=None,
    voice_id=None,
) -> Review:
    found = check_review_eligibility(author, kind, transaction_id)
    try:
        with transaction.atomic():
            review = Review.objects.create(
                author=author,
                pro_id=found.pro_id,
                source_type=kind,
                source_id=found.id,
                rating=max(1, min(5, int(rating))),
                text=text.strip(),
                photo=_review_media(author, photo_id, "review_photo"),
                voice=_review_media(author, voice_id, "review_voice"),
            )
    except IntegrityError as exc:
        raise errors.AlreadyReviewed() from exc
    screen(review, text=review.text, language=_language(author))
    recompute_rating(found.pro_id)
    review.refresh_from_db()
    if review.visibility == Visibility.VISIBLE:
        notify(
            review.pro.user,
            "reviews.received",
            {"name": author.first_name or "?", "rating": review.rating},
            link="/pro",
        )
    return review


@transaction.atomic
def reply_to_review(review: Review, actor, text: str) -> Review:
    if review.pro.user_id != actor.pk:
        raise errors.NotYours()
    if review.replied_at is not None:
        raise errors.AlreadyReplied()
    review.reply = text.strip()
    review.replied_at = timezone.now()
    review.save(update_fields=["reply", "replied_at", "updated_at"])
    screen(review, text=review.reply, language=_language(actor))
    notify(review.author, "reviews.replied", {"name": review.pro.display_name}, link=None)
    return review


@transaction.atomic
def rate_client(
    pro: ProProfile,
    *,
    kind: str,
    transaction_id,
    rating: int,
    no_show: bool = False,
    note: str = "",
) -> ClientRating:
    """Private rating of a client after a finished transaction with this pro."""
    found = _transaction(kind, transaction_id)
    if found.pro_id != pro.pk:
        raise errors.NotYourTransaction()
    if found.finished_at is None and not no_show:
        raise errors.NotFinished()
    rating_row, _ = ClientRating.objects.update_or_create(
        source_type=kind,
        source_id=found.id,
        defaults={
            "pro": pro,
            "client_id": found.client_id,
            "rating": max(1, min(5, int(rating))),
            "no_show": no_show,
            "note": note.strip()[:300],
        },
    )
    return rating_row
