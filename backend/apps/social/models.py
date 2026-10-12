from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Visibility(models.TextChoices):
    """Moderation state shared by posts, comments, stories and reviews."""

    VISIBLE = "visible", _("Visible")
    HELD = "held", _("Held for review")
    REMOVED = "removed", _("Removed")


def _user_fk(related_name, verbose_name):
    return models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=related_name,
        verbose_name=verbose_name,
    )


class Post(BaseModel):
    """A post of a pro or a client: picture, carousel, short video or before/after."""

    class Kind(models.TextChoices):
        PHOTO = "photo", _("Picture")
        CAROUSEL = "carousel", _("Carousel")
        VIDEO = "video", _("Short video")
        BEFORE_AFTER = "before_after", _("Before / after")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SCHEDULED = "scheduled", _("Scheduled")
        PUBLISHED = "published", _("Published")

    author = _user_fk("posts", _("author"))
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("pro"),
        help_text=_("Set when the author posts as a pro."),
    )
    kind = models.CharField(_("type"), max_length=14, choices=Kind.choices)
    caption = models.TextField(_("caption"), max_length=2200, blank=True)
    trade = models.ForeignKey(
        "pros.Trade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("trade"),
    )
    # « Book this look ».
    service = models.ForeignKey(
        "pros.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("service"),
    )
    # « Buy this product »: a product of the shop module, linked when it exists.
    product_id = models.UUIDField(_("product"), null=True, blank=True)

    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    publish_at = models.DateTimeField(_("to publish at"), null=True, blank=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True, db_index=True)
    visibility = models.CharField(
        _("moderation"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    # Where it comes from, for the « trending in my city / my country » parts of the feed.
    city = models.CharField(_("city"), max_length=80, blank=True, db_index=True)
    country = models.ForeignKey(
        "core.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("country"),
    )
    location = gis_models.PointField(_("position"), geography=True, null=True, blank=True)

    like_count = models.PositiveIntegerField(_("likes"), default=0)
    comment_count = models.PositiveIntegerField(_("comments"), default=0)
    save_count = models.PositiveIntegerField(_("saves"), default=0)
    share_count = models.PositiveIntegerField(_("shares"), default=0)

    class Meta:
        verbose_name = _("post")
        verbose_name_plural = _("posts")
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "visibility", "-published_at"])]

    def __str__(self):
        return (self.caption or str(self.pk))[:60]

    @property
    def is_live(self) -> bool:
        return (
            self.status == self.Status.PUBLISHED
            and self.visibility == Visibility.VISIBLE
            and self.deleted_at is None
        )


class PostMedia(BaseModel):
    class Role(models.TextChoices):
        ITEM = "item", _("Picture or video")
        BEFORE = "before", _("Before")
        AFTER = "after", _("After")

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="media_items", verbose_name=_("post")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("file")
    )
    role = models.CharField(_("role"), max_length=6, choices=Role.choices, default=Role.ITEM)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("post file")
        verbose_name_plural = _("post files")
        ordering = ["position"]


class Like(BaseModel):
    user = _user_fk("likes", _("person"))
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        verbose_name = _("like")
        verbose_name_plural = _("likes")
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="social_like_once")]


class SavedPost(BaseModel):
    user = _user_fk("saved_posts", _("person"))
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saves")

    class Meta:
        verbose_name = _("saved post")
        verbose_name_plural = _("saved posts")
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="social_save_once")]


class Share(BaseModel):
    class Network(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        FACEBOOK = "facebook", "Facebook"
        TIKTOK = "tiktok", "TikTok"
        LINK = "link", _("Copied link")
        OTHER = "other", _("Other")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="shares")
    network = models.CharField(_("network"), max_length=10, choices=Network.choices)

    class Meta:
        verbose_name = _("share")
        verbose_name_plural = _("shares")


class Comment(BaseModel):
    """A comment; a reply has a parent (one level of replies)."""

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments", verbose_name=_("post")
    )
    author = _user_fk("comments", _("author"))
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("reply to"),
    )
    text = models.TextField(_("text"), max_length=1000)
    visibility = models.CharField(
        _("moderation"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ["created_at"]

    def __str__(self):
        return self.text[:60]

    def on_visibility_change(self):
        from .services import recount_comments

        recount_comments(self.post_id)


class Follow(BaseModel):
    follower = _user_fk("following", _("follower"))
    followed = _user_fk("followers", _("followed"))

    class Meta:
        verbose_name = _("follow")
        verbose_name_plural = _("follows")
        constraints = [
            models.UniqueConstraint(fields=["follower", "followed"], name="social_follow_once"),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("followed")), name="social_no_self_follow"
            ),
        ]


class Story(BaseModel):
    """Visible 24 hours: a picture, a video, a text on a colour, or today's free slots."""

    class Kind(models.TextChoices):
        PHOTO = "photo", _("Picture")
        VIDEO = "video", _("Video")
        TEXT = "text", _("Text")
        FREE_SLOTS = "free_slots", _("Free slots today")

    class Background(models.TextChoices):
        HIBISCUS = "hibiscus", _("Hibiscus")
        PRUNE = "prune", _("Plum")
        OR = "or", _("Gold")
        FEUILLE = "feuille", _("Leaf")
        POUDRE = "poudre", _("Powder")

    author = _user_fk("stories", _("author"))
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
        verbose_name=_("pro"),
    )
    kind = models.CharField(_("type"), max_length=10, choices=Kind.choices)
    media = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("file"),
    )
    text = models.CharField(_("text"), max_length=200, blank=True)
    background = models.CharField(
        _("background"), max_length=8, choices=Background.choices, default=Background.HIBISCUS
    )
    slots = models.JSONField(
        _("free slots"), default=list, blank=True, help_text=_('Times of today, e.g. ["14:00"].')
    )
    expires_at = models.DateTimeField(_("expires at"), db_index=True)
    city = models.CharField(_("city"), max_length=80, blank=True)
    country = models.ForeignKey(
        "core.Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    visibility = models.CharField(
        _("moderation"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )

    class Meta:
        verbose_name = _("story")
        verbose_name_plural = _("stories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author} ({self.get_kind_display()})"


class StoryView(BaseModel):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    user = _user_fk("story_views", _("person"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["story", "user"], name="social_story_seen_once")
        ]


class TransactionKind(models.TextChoices):
    """Transactions that open the right to a review (booking and shop modules)."""

    BOOKING = "booking", _("Booking")
    ORDER = "order", _("Order")


class Review(BaseModel):
    """A verified review: only for a finished booking or order of the author."""

    author = _user_fk("reviews", _("author"))
    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="reviews", verbose_name=_("pro")
    )
    source_type = models.CharField(_("for a"), max_length=10, choices=TransactionKind.choices)
    source_id = models.UUIDField(_("transaction"))
    rating = models.PositiveSmallIntegerField(
        _("stars"), validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(_("text"), max_length=2000, blank=True)
    photo = models.ForeignKey(
        "core.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    voice = models.ForeignKey(
        "core.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reply = models.TextField(_("reply of the pro"), max_length=1000, blank=True)
    replied_at = models.DateTimeField(_("replied at"), null=True, blank=True)
    visibility = models.CharField(
        _("moderation"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )

    class Meta:
        verbose_name = _("review")
        verbose_name_plural = _("reviews")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"], name="social_one_review_per_transaction"
            )
        ]

    def __str__(self):
        return f"{self.rating}/5 {self.pro}"

    def on_visibility_change(self):
        from .services import recompute_rating

        recompute_rating(self.pro_id)


class ClientRating(BaseModel):
    """How a pro rates a client after a transaction. Private: used for deposit rules."""

    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="client_ratings",
        verbose_name=_("pro"),
    )
    client = _user_fk("ratings_received", _("client"))
    source_type = models.CharField(_("for a"), max_length=10, choices=TransactionKind.choices)
    source_id = models.UUIDField(_("transaction"))
    rating = models.PositiveSmallIntegerField(
        _("stars"), validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    no_show = models.BooleanField(_("did not come"), default=False)
    note = models.CharField(_("private note"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("client rating")
        verbose_name_plural = _("client ratings")
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"], name="social_one_client_rating_per_transaction"
            )
        ]
