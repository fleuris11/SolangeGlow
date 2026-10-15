from __future__ import annotations

from urllib.parse import quote

from django.contrib.gis.geos import Point
from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.pros import errors as pro_errors
from apps.pros import services as pro_services
from apps.pros.models import ProProfile
from apps.pros.search import decode_cursor, encode_cursor

from . import errors, selectors, services
from . import serializers as s
from .feed import feed
from .models import Comment, Follow, Post, Review, StoryView

AUTHOR_RELATED = ("author", "author__photo", "author__pro_profile", "author__pro_profile__photo")


def _page(request) -> tuple[int, int]:
    return decode_cursor(request.query_params.get("cursor")), 20


def _posts_payload(posts, viewer) -> list[dict]:
    authors = {post.author_id for post in posts}
    story_authors = selectors.has_live_story(authors)
    followed = (
        set(Follow.objects.filter(follower=viewer).values_list("followed_id", flat=True))
        if viewer is not None and viewer.is_authenticated
        else set()
    )
    return [
        s.post_payload(post, viewer, story_authors=story_authors, followed=followed)
        for post in posts
    ]


class SocialWriteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "social_write"


# --- Feed and posts ----------------------------------------------------------------------------


class FeedView(OptionalAuthView):
    """Followed people, then trending in her city, then her country (cursor pages)."""

    @extend_schema(
        tags=["social"],
        parameters=[
            OpenApiParameter("cursor", str, required=False),
            OpenApiParameter("city", str, required=False),
            OpenApiParameter("country", str, required=False),
            OpenApiParameter("lat", float, required=False),
            OpenApiParameter("lng", float, required=False),
        ],
        responses=s.PostPageSerializer,
    )
    def get(self, request):
        params = request.query_params
        near = None
        try:
            if params.get("lat") and params.get("lng"):
                near = Point(float(params["lng"]), float(params["lat"]), srid=4326)
        except ValueError:
            near = None
        rows, next_cursor = feed(
            request.user,
            city=params.get("city", "")[:80],
            country=params.get("country", "")[:2].upper(),
            near=near,
            cursor=params.get("cursor"),
        )
        ids = [row.pk for row in rows]
        flagged = {
            post.pk: post
            for post in selectors.with_viewer_flags(
                Post.objects.filter(pk__in=ids).select_related(*AUTHOR_RELATED, "trade", "service"),
                request.user,
            ).prefetch_related("media_items__media")
        }
        posts = [flagged[pk] for pk in ids if pk in flagged]
        return Response({"results": _posts_payload(posts, request.user), "next": next_cursor})


class PostCreateView(SocialWriteView):
    @extend_schema(
        tags=["social"], request=s.PostCreateSerializer, responses={201: s.PostSerializer}
    )
    def post(self, request):
        data = s.PostCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        post = services.create_post(
            request.user,
            kind=values["kind"],
            media=[dict(item) for item in values["media"]],
            caption=values.get("caption", ""),
            trade_key=values.get("trade") or None,
            service_id=values.get("service_id"),
            product_id=values.get("product_id"),
            status=values["status"],
            publish_at=values.get("publish_at"),
        )
        post = selectors.post_detail(post.pk).get()
        return Response(_posts_payload([post], request.user)[0], status=status.HTTP_201_CREATED)


class PostView(OptionalAuthView):
    throttle_scope = None
    throttle_classes = []

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method != "GET" else super().get_permissions()

    def _post(self, request, post_id) -> Post:
        services.live_post(post_id, request.user)
        return selectors.with_viewer_flags(selectors.post_detail(post_id), request.user).get()

    @extend_schema(tags=["social"], responses=s.PostSerializer)
    def get(self, request, post_id):
        return Response(_posts_payload([self._post(request, post_id)], request.user)[0])

    @extend_schema(tags=["social"], request=s.PostUpdateSerializer, responses=s.PostSerializer)
    def patch(self, request, post_id):
        data = s.PostUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        changes = dict(data.validated_data)
        if "trade" in changes:
            changes["trade_key"] = changes.pop("trade")
        post = get_object_or_404(Post, pk=post_id, deleted_at__isnull=True)
        services.update_post(post, request.user, **changes)
        return Response(_posts_payload([self._post(request, post_id)], request.user)[0])

    @extend_schema(tags=["social"], request=None, responses={204: None})
    def delete(self, request, post_id):
        services.delete_post(
            get_object_or_404(Post, pk=post_id, deleted_at__isnull=True), request.user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPostsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("status", str, required=False)],
        responses=s.PostPageSerializer,
    )
    def get(self, request):
        posts = list(
            selectors.my_posts(request.user, request.query_params.get("status")).select_related(
                *AUTHOR_RELATED, "trade", "service"
            )[:60]
        )
        return Response({"results": _posts_payload(posts, request.user), "next": None})


class SavedPostsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses=s.PostPageSerializer,
    )
    def get(self, request):
        offset, size = _page(request)
        posts = selectors.with_viewer_flags(
            selectors.saved_posts(request.user).select_related(*AUTHOR_RELATED, "trade", "service"),
            request.user,
        ).prefetch_related("media_items__media")
        rows = list(posts[offset : offset + size + 1])
        return Response(
            {
                "results": _posts_payload(rows[:size], request.user),
                "next": encode_cursor(offset + size) if len(rows) > size else None,
            }
        )


class PersonPostsView(OptionalAuthView):
    """Posts of one person (a pro's showcase shows them under « Publications »)."""

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses=s.PostPageSerializer,
    )
    def get(self, request, user_id):
        author = get_object_or_404(User, pk=user_id, is_active=True)
        offset, size = _page(request)
        posts = selectors.with_viewer_flags(
            selectors.posts_of(author, request.user).select_related(
                *AUTHOR_RELATED, "trade", "service"
            ),
            request.user,
        ).prefetch_related("media_items__media")
        rows = list(posts[offset : offset + size + 1])
        return Response(
            {
                "results": _posts_payload(rows[:size], request.user),
                "next": encode_cursor(offset + size) if len(rows) > size else None,
            }
        )


def _counts(post, user) -> dict:
    return {
        "like_count": post.like_count,
        "save_count": post.save_count,
        "liked": post.likes.filter(user=user).exists(),
        "saved": post.saves.filter(user=user).exists(),
    }


class LikeView(SocialWriteView):
    @extend_schema(tags=["social"], request=None, responses=s.CountsSerializer)
    def post(self, request, post_id):
        post = services.live_post(post_id, request.user)
        return Response(_counts(services.like(request.user, post), request.user))

    @extend_schema(tags=["social"], request=None, responses={200: s.CountsSerializer})
    def delete(self, request, post_id):
        post = services.live_post(post_id, request.user)
        return Response(_counts(services.unlike(request.user, post), request.user))


class SaveView(SocialWriteView):
    @extend_schema(tags=["social"], request=None, responses=s.CountsSerializer)
    def post(self, request, post_id):
        post = services.live_post(post_id, request.user)
        return Response(_counts(services.save(request.user, post), request.user))

    @extend_schema(tags=["social"], request=None, responses={200: s.CountsSerializer})
    def delete(self, request, post_id):
        post = services.live_post(post_id, request.user)
        return Response(_counts(services.unsave(request.user, post), request.user))


class ShareView(OptionalAuthView):
    """Counts a share and gives the links (WhatsApp, Facebook; TikTok uses the copied link)."""

    throttle_scope = "social_write"

    @extend_schema(
        tags=["social"], request=s.ShareRequestSerializer, responses=s.ShareLinksSerializer
    )
    def post(self, request, post_id):
        post = services.live_post(post_id, request.user)
        data = s.ShareRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.record_share(request.user, post, data.validated_data["network"])
        url = s.share_url(post)
        return Response(
            {
                "url": url,
                "whatsapp": f"https://wa.me/?text={quote(url)}",
                "facebook": f"https://www.facebook.com/sharer/sharer.php?u={quote(url)}",
            }
        )


# --- Comments ----------------------------------------------------------------------------------


class CommentsView(OptionalAuthView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else super().get_permissions()

    def get_throttles(self):
        self.throttle_scope = "social_write" if self.request.method == "POST" else "search"
        return super().get_throttles()

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses=s.CommentPageSerializer,
    )
    def get(self, request, post_id):
        post = services.live_post(post_id, request.user)
        offset, size = _page(request)
        rows = list(selectors.comments_of(post, request.user)[offset : offset + size + 1])
        return Response(
            {
                "results": [s.comment_payload(item, request.user) for item in rows[:size]],
                "next": encode_cursor(offset + size) if len(rows) > size else None,
            }
        )

    @extend_schema(
        tags=["social"], request=s.CommentCreateSerializer, responses={201: s.ReplySerializer}
    )
    def post(self, request, post_id):
        post = services.live_post(post_id, request.user)
        data = s.CommentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        item = services.comment(
            request.user,
            post,
            data.validated_data["text"],
            parent_id=data.validated_data.get("parent_id"),
        )
        return Response(
            s.comment_payload(item, request.user, with_replies=False),
            status=status.HTTP_201_CREATED,
        )


class CommentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["social"], request=None, responses={204: None})
    def delete(self, request, comment_id):
        item = Comment.objects.filter(pk=comment_id, deleted_at__isnull=True).first()
        if item is None:
            raise errors.CommentNotFound()
        services.delete_comment(item, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Follows -------------------------------------------------------------------------------------


class FollowView(SocialWriteView):
    @extend_schema(tags=["social"], request=None, responses={204: None})
    def post(self, request, user_id):
        services.follow(request.user, get_object_or_404(User, pk=user_id, is_active=True))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["social"], request=None, responses={204: None})
    def delete(self, request, user_id):
        services.unfollow(request.user, get_object_or_404(User, pk=user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["social"], responses=s.FollowingSerializer(many=True))
    def get(self, request):
        people = list(selectors.following_of(request.user)[:200])
        stories = selectors.has_live_story([p.pk for p in people])
        ids = {p.pk for p in people}
        return Response(
            [
                {
                    **s.author_payload(p, story_authors=stories, followed=ids),
                    "post_count": p.post_count,
                }
                for p in people
            ]
        )


# --- Stories -------------------------------------------------------------------------------------


class StoriesView(OptionalAuthView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else super().get_permissions()

    def get_throttles(self):
        self.throttle_scope = "social_write" if self.request.method == "POST" else "search"
        return super().get_throttles()

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("city", str, required=False)],
        responses=s.StoryGroupSerializer(many=True),
    )
    def get(self, request):
        tray = selectors.story_tray(request.user, city=request.query_params.get("city", "")[:80])
        seen = (
            set(StoryView.objects.filter(user=request.user).values_list("story_id", flat=True))
            if request.user.is_authenticated
            else set()
        )
        authors = {entry["author"].pk for entry in tray}
        return Response(
            [
                {
                    "author": s.author_payload(entry["author"], story_authors=authors),
                    "stories": [s.story_payload(x, request.user, seen) for x in entry["stories"]],
                    "seen": entry["seen"],
                }
                for entry in tray
            ]
        )

    @extend_schema(
        tags=["social"], request=s.StoryCreateSerializer, responses={201: s.StorySerializer}
    )
    def post(self, request):
        data = s.StoryCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        story = services.create_story(request.user, **data.validated_data)
        return Response(s.story_payload(story, request.user), status=status.HTTP_201_CREATED)


class StoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["social"], request=None, responses={204: None})
    def delete(self, request, story_id):
        story = get_object_or_404(selectors.live_stories(), pk=story_id)
        services.delete_story(story, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StorySeenView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["social"], request=None, responses={204: None})
    def post(self, request, story_id):
        services.mark_seen(get_object_or_404(selectors.live_stories(), pk=story_id), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Reviews -------------------------------------------------------------------------------------


class ProReviewsView(OptionalAuthView):
    @extend_schema(
        tags=["reviews"],
        parameters=[OpenApiParameter("cursor", str, required=False)],
        responses=s.ReviewPageSerializer,
    )
    def get(self, request, slug):
        pro = ProProfile.objects.filter(
            slug=slug.lower(), status=ProProfile.Status.PUBLISHED
        ).first()
        if pro is None:
            raise pro_errors.ProNotFound()
        reviews = selectors.reviews_of(pro)
        offset, size = _page(request)
        rows = list(reviews[offset : offset + size + 1])
        counts = dict(
            reviews.values_list("rating").annotate(n=Count("pk")).values_list("rating", "n")
        )
        return Response(
            {
                "average": float(pro.rating_average) if pro.rating_average is not None else None,
                "count": pro.rating_count,
                "distribution": {str(star): counts.get(star, 0) for star in range(1, 6)},
                "results": [s.review_payload(review) for review in rows[:size]],
                "next": encode_cursor(offset + size) if len(rows) > size else None,
            }
        )


class PendingReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["reviews"], responses=s.PendingReviewSerializer(many=True))
    def get(self, request):
        pending = services.pending_reviews(request.user)
        pros = {p.pk: p for p in ProProfile.objects.filter(pk__in={t.pro_id for t in pending})}
        return Response(
            [
                {
                    "kind": t.kind,
                    "transaction_id": t.id,
                    "label": t.label,
                    "finished_at": t.finished_at,
                    "pro_slug": pros[t.pro_id].slug if t.pro_id in pros else None,
                    "pro_name": pros[t.pro_id].display_name if t.pro_id in pros else "",
                }
                for t in pending
            ]
        )


class ReviewCreateView(SocialWriteView):
    @extend_schema(
        tags=["reviews"], request=s.ReviewCreateSerializer, responses={201: s.ReviewSerializer}
    )
    def post(self, request):
        data = s.ReviewCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        review = services.create_review(
            request.user,
            kind=values["kind"],
            transaction_id=values["transaction_id"],
            rating=values["rating"],
            text=values.get("text", ""),
            photo_id=values.get("photo_id"),
            voice_id=values.get("voice_id"),
        )
        return Response(s.review_payload(review), status=status.HTTP_201_CREATED)


class ReviewReplyView(SocialWriteView):
    @extend_schema(tags=["reviews"], request=s.ReviewReplySerializer, responses=s.ReviewSerializer)
    def post(self, request, review_id):
        review = Review.objects.filter(pk=review_id).select_related("pro", "author").first()
        if review is None:
            raise errors.ReviewNotFound()
        data = s.ReviewReplySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.reply_to_review(review, request.user, data.validated_data["text"])
        return Response(s.review_payload(review))


class ClientRatingView(SocialWriteView):
    """The pro rates a client after a finished booking (private)."""

    @extend_schema(tags=["reviews"], request=s.ClientRatingSerializer, responses={204: None})
    def post(self, request):
        data = s.ClientRatingSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        services.rate_client(
            pro_services.get_pro(request.user),
            kind=values["kind"],
            transaction_id=values["transaction_id"],
            rating=values["rating"],
            no_show=values.get("no_show", False),
            note=values.get("note", ""),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
