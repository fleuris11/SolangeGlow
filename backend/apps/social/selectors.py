from __future__ import annotations

from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet
from django.utils import timezone

from apps.moderation.selectors import blocked_user_ids, hidden_ids

from .feed import live_posts, visible_to
from .models import Comment, Follow, Like, Post, Review, SavedPost, Story, StoryView, Visibility


def with_viewer_flags(queryset: QuerySet[Post], viewer) -> QuerySet[Post]:
    """Adds liked / saved / follows_author for the person looking (False for visitors)."""
    if viewer is None or not viewer.is_authenticated:
        return queryset
    return queryset.annotate(
        viewer_liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=viewer)),
        viewer_saved=Exists(SavedPost.objects.filter(post=OuterRef("pk"), user=viewer)),
        viewer_follows=Exists(
            Follow.objects.filter(followed=OuterRef("author_id"), follower=viewer)
        ),
    )


def post_detail(post_id) -> QuerySet[Post]:
    return (
        Post.objects.filter(pk=post_id)
        .select_related("author", "author__photo", "pro", "pro__photo", "trade", "service")
        .prefetch_related("media_items__media")
    )


def posts_of(author, viewer=None) -> QuerySet[Post]:
    return visible_to(viewer, live_posts().filter(author=author)).order_by("-published_at")


def my_posts(user, status: str | None = None) -> QuerySet[Post]:
    posts = Post.objects.filter(author=user, deleted_at__isnull=True).prefetch_related(
        "media_items__media"
    )
    if status:
        posts = posts.filter(status=status)
    return posts.order_by("-created_at")


def saved_posts(user) -> QuerySet[Post]:
    return visible_to(user, live_posts().filter(saves__user=user)).order_by("-saves__created_at")


def comments_of(post: Post, viewer=None) -> QuerySet[Comment]:
    blocked = blocked_user_ids(viewer)
    hidden = hidden_ids(viewer, Comment)
    replies = (
        Comment.objects.filter(deleted_at__isnull=True, visibility=Visibility.VISIBLE)
        .exclude(author_id__in=blocked)
        .exclude(pk__in=hidden)
        .select_related("author", "author__photo")
        .order_by("created_at")
    )
    return (
        Comment.objects.filter(
            post=post, parent__isnull=True, deleted_at__isnull=True, visibility=Visibility.VISIBLE
        )
        .exclude(author_id__in=blocked)
        .exclude(pk__in=hidden)
        .select_related("author", "author__photo")
        .prefetch_related(Prefetch("replies", queryset=replies, to_attr="visible_replies"))
        .order_by("created_at", "pk")
    )


def live_stories() -> QuerySet[Story]:
    return Story.objects.filter(expires_at__gt=timezone.now(), visibility=Visibility.VISIBLE)


def story_tray(viewer=None, *, city: str = "") -> list[dict]:
    """Authors with live stories: followed people first, then her city, then the others.

    Each entry: author, her stories (oldest first), and whether all were seen.
    """
    stories = (
        live_stories()
        .filter(author__is_active=True)
        .select_related("author", "author__photo", "pro", "pro__photo", "media")
    )
    followed: set = set()
    seen: set = set()
    if viewer is not None and viewer.is_authenticated:
        city = city or viewer.city
        stories = stories.exclude(author_id__in=blocked_user_ids(viewer))
        followed = set(Follow.objects.filter(follower=viewer).values_list("followed_id", flat=True))
        seen = set(StoryView.objects.filter(user=viewer).values_list("story_id", flat=True))
    groups: dict = {}
    for story in stories.order_by("created_at"):
        groups.setdefault(story.author_id, []).append(story)

    def rank(item):
        author_id, items = item
        return (
            0
            if author_id in followed
            else 1
            if city and items[0].city.lower() == city.lower()
            else 2,
            all(s.pk in seen for s in items),
            -items[-1].created_at.timestamp(),
        )

    return [
        {"author": items[0].author, "pro": items[0].pro, "stories": items,
         "seen": all(s.pk in seen for s in items)}
        for _author_id, items in sorted(groups.items(), key=rank)
    ]  # fmt: skip


def has_live_story(user_ids) -> set:
    return set(live_stories().filter(author_id__in=user_ids).values_list("author_id", flat=True))


def following_of(user) -> QuerySet:
    from apps.accounts.models import User

    return (
        User.objects.filter(followers__follower=user, is_active=True)
        .select_related("photo", "pro_profile", "pro_profile__photo")
        .annotate(post_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED)))
        .order_by("-followers__created_at")
    )


def follower_count(user) -> int:
    return Follow.objects.filter(followed=user).count()


def reviews_of(pro) -> QuerySet[Review]:
    return (
        Review.objects.filter(pro=pro, visibility=Visibility.VISIBLE)
        .select_related("author", "author__photo", "photo", "voice")
        .order_by("-created_at", "pk")
    )


def client_reliability(user) -> dict:
    """Private: how pros rated her (deposit rules of the booking module will use it)."""
    from django.db.models import Avg

    from .models import ClientRating

    stats = ClientRating.objects.filter(client=user).aggregate(
        average=Avg("rating"), count=Count("pk"), no_shows=Count("pk", filter=Q(no_show=True))
    )
    return {
        "average": float(stats["average"]) if stats["average"] is not None else None,
        "count": stats["count"],
        "no_shows": stats["no_shows"],
    }
