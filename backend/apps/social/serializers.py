from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext
from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.pros.serializers import TradeSerializer

from . import products
from .models import Post, PostMedia, Share, Story, TransactionKind

Media = MediaSerializer(allow_null=True)


# --- People ----------------------------------------------------------------------------------


class AuthorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    is_pro = serializers.BooleanField()
    pro_slug = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    has_story = serializers.BooleanField()
    followed = serializers.BooleanField()


def member_name(user) -> str:
    """First name, or a neutral name for someone who has not given one yet."""
    return user.first_name or gettext("Solange Glow member")


def author_payload(user, *, story_authors=frozenset(), followed=frozenset()) -> dict:
    pro = getattr(user, "_pro", None)
    if pro is None:
        try:
            pro = user.pro_profile
        except ObjectDoesNotExist:  # no showcase
            pro = None
    published = pro is not None and pro.is_published
    photo = (pro.photo if published and pro.photo_id else None) or user.photo
    return {
        "id": user.pk,
        "name": (pro.display_name if published else "") or member_name(user),
        "photo": asset_payload(photo) if photo is not None and photo.is_ready else None,
        "is_pro": published,
        "pro_slug": pro.slug if published else None,
        "verified": bool(published and pro.is_verified),
        "has_story": user.pk in story_authors,
        "followed": user.pk in followed,
    }


class FollowingSerializer(AuthorSerializer):
    post_count = serializers.IntegerField()


# --- Posts -----------------------------------------------------------------------------------


class PostMediaSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=PostMedia.Role.choices)
    media = MediaSerializer()


class LinkedServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    price_kind = serializers.CharField()
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    duration_minutes = serializers.IntegerField()


class LinkedProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    price_minor = serializers.IntegerField()
    before_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    picture = MediaSerializer(allow_null=True)
    in_stock = serializers.BooleanField()
    link = serializers.CharField()


class PostSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Post.Kind.choices)
    caption = serializers.CharField()
    trade = TradeSerializer(allow_null=True)
    service = LinkedServiceSerializer(allow_null=True)
    product_id = serializers.UUIDField(allow_null=True)
    product = LinkedProductSerializer(allow_null=True)
    status = serializers.ChoiceField(choices=Post.Status.choices)
    publish_at = serializers.DateTimeField(allow_null=True)
    published_at = serializers.DateTimeField(allow_null=True)
    visibility = serializers.CharField()
    city = serializers.CharField()
    media = PostMediaSerializer(many=True)
    author = AuthorSerializer()
    like_count = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    save_count = serializers.IntegerField()
    share_count = serializers.IntegerField()
    liked = serializers.BooleanField()
    saved = serializers.BooleanField()
    is_mine = serializers.BooleanField()
    share_url = serializers.CharField()


def share_url(post: Post) -> str:
    return f"{settings.SHORT_LINK_BASE_URL.rstrip('/')}/p/{post.pk}"


def post_payload(post: Post, viewer=None, *, story_authors=frozenset(), followed=frozenset()):
    signed_in = viewer is not None and viewer.is_authenticated
    service = post.service
    items = sorted(post.media_items.all(), key=lambda item: item.position)
    return {
        "id": post.pk,
        "kind": post.kind,
        "caption": post.caption,
        "trade": TradeSerializer(post.trade).data if post.trade_id else None,
        "service": {
            "id": service.pk,
            "name": service.name,
            "price_kind": service.price_kind,
            "price_minor": service.price_minor,
            "currency": service.currency,
            "duration_minutes": service.duration_minutes,
        }
        if service is not None and service.is_active and service.archived_at is None
        else None,
        "product_id": post.product_id,
        "product": products.card(post.product_id),
        "status": post.status,
        "publish_at": post.publish_at,
        "published_at": post.published_at,
        "visibility": post.visibility,
        "city": post.city,
        "media": [{"role": item.role, "media": asset_payload(item.media)} for item in items],
        "author": author_payload(post.author, story_authors=story_authors, followed=followed),
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "save_count": post.save_count,
        "share_count": post.share_count,
        "liked": bool(getattr(post, "viewer_liked", False)) if signed_in else False,
        "saved": bool(getattr(post, "viewer_saved", False)) if signed_in else False,
        "is_mine": signed_in and post.author_id == viewer.pk,
        "share_url": share_url(post),
    }


class PostPageSerializer(serializers.Serializer):
    results = PostSerializer(many=True)
    next = serializers.CharField(allow_null=True)


class PostMediaInputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=PostMedia.Role.choices, required=False)


class PostCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Post.Kind.choices)
    media = PostMediaInputSerializer(many=True)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=2200)
    trade = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    service_id = serializers.UUIDField(required=False, allow_null=True)
    product_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Post.Status.choices, default=Post.Status.PUBLISHED)
    publish_at = serializers.DateTimeField(required=False, allow_null=True)


class PostUpdateSerializer(serializers.Serializer):
    caption = serializers.CharField(required=False, allow_blank=True, max_length=2200)
    trade = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    service_id = serializers.UUIDField(required=False, allow_null=True)
    product_id = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Post.Status.choices, required=False)
    publish_at = serializers.DateTimeField(required=False, allow_null=True)


class CountsSerializer(serializers.Serializer):
    like_count = serializers.IntegerField()
    save_count = serializers.IntegerField()
    liked = serializers.BooleanField()
    saved = serializers.BooleanField()


class ShareRequestSerializer(serializers.Serializer):
    network = serializers.ChoiceField(choices=Share.Network.choices)


class ShareLinksSerializer(serializers.Serializer):
    url = serializers.CharField()
    whatsapp = serializers.CharField()
    facebook = serializers.CharField()


# --- Comments --------------------------------------------------------------------------------


class ReplySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    author = AuthorSerializer()
    created_at = serializers.DateTimeField()
    is_mine = serializers.BooleanField()


class CommentSerializer(ReplySerializer):
    replies = ReplySerializer(many=True)


def comment_payload(item, viewer=None, *, with_replies=True) -> dict:
    signed_in = viewer is not None and viewer.is_authenticated
    data = {
        "id": item.pk,
        "text": item.text,
        "author": author_payload(item.author),
        "created_at": item.created_at,
        "is_mine": signed_in and item.author_id == viewer.pk,
    }
    if with_replies:
        data["replies"] = [
            comment_payload(reply, viewer, with_replies=False)
            for reply in getattr(item, "visible_replies", [])
        ]
    return data


class CommentPageSerializer(serializers.Serializer):
    results = CommentSerializer(many=True)
    next = serializers.CharField(allow_null=True)


class CommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


# --- Stories ---------------------------------------------------------------------------------


class StorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Story.Kind.choices)
    media = MediaSerializer(allow_null=True)
    text = serializers.CharField()
    background = serializers.ChoiceField(choices=Story.Background.choices)
    slots = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    seen = serializers.BooleanField()
    is_mine = serializers.BooleanField()


class StoryGroupSerializer(serializers.Serializer):
    author = AuthorSerializer()
    stories = StorySerializer(many=True)
    seen = serializers.BooleanField()


def story_payload(story: Story, viewer=None, seen=frozenset()) -> dict:
    signed_in = viewer is not None and viewer.is_authenticated
    return {
        "id": story.pk,
        "kind": story.kind,
        "media": asset_payload(story.media) if story.media_id else None,
        "text": story.text,
        "background": story.background,
        "slots": story.slots,
        "created_at": story.created_at,
        "expires_at": story.expires_at,
        "seen": story.pk in seen,
        "is_mine": signed_in and story.author_id == viewer.pk,
    }


class StoryCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Story.Kind.choices)
    media_id = serializers.UUIDField(required=False, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, max_length=200)
    background = serializers.ChoiceField(choices=Story.Background.choices, required=False)
    slots = serializers.ListField(child=serializers.CharField(max_length=5), required=False)


# --- Reviews ---------------------------------------------------------------------------------


class ReviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    rating = serializers.IntegerField()
    text = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    voice = MediaSerializer(allow_null=True)
    author_name = serializers.CharField()
    author_photo = MediaSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    reply = serializers.CharField()
    replied_at = serializers.DateTimeField(allow_null=True)


def review_payload(review) -> dict:
    photo = review.author.photo
    return {
        "id": review.pk,
        "rating": review.rating,
        "text": review.text,
        "photo": asset_payload(review.photo) if review.photo_id and review.photo.is_ready else None,
        "voice": asset_payload(review.voice) if review.voice_id and review.voice.is_ready else None,
        "author_name": member_name(review.author),
        "author_photo": asset_payload(photo) if photo is not None and photo.is_ready else None,
        "created_at": review.created_at,
        "reply": review.reply,
        "replied_at": review.replied_at,
    }


class ReviewPageSerializer(serializers.Serializer):
    average = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()
    distribution = serializers.DictField(child=serializers.IntegerField())
    results = ReviewSerializer(many=True)
    next = serializers.CharField(allow_null=True)


class ReviewCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=TransactionKind.choices)
    transaction_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    photo_id = serializers.UUIDField(required=False, allow_null=True)
    voice_id = serializers.UUIDField(required=False, allow_null=True)


class ReviewReplySerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)


class PendingReviewSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=TransactionKind.choices)
    transaction_id = serializers.UUIDField()
    label = serializers.CharField()
    finished_at = serializers.DateTimeField()
    pro_slug = serializers.CharField(allow_null=True)
    pro_name = serializers.CharField()


class ClientRatingSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=TransactionKind.choices)
    transaction_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    no_show = serializers.BooleanField(required=False, default=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)
