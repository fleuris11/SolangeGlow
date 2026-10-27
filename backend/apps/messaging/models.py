from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Conversation(BaseModel):
    """A private discussion between two people, or a group (dispute rooms, support)."""

    class Kind(models.TextChoices):
        DIRECT = "direct", _("Between two people")
        GROUP = "group", _("Group")

    class Purpose(models.TextChoices):
        CHAT = "chat", _("Discussion")
        DISPUTE = "dispute", _("Dispute room")
        SUPPORT = "support", _("Support")

    kind = models.CharField(_("type"), max_length=8, choices=Kind.choices)
    purpose = models.CharField(
        _("purpose"), max_length=10, choices=Purpose.choices, default=Purpose.CHAT
    )
    # Two people share one direct conversation: "<smaller id>:<bigger id>".
    direct_key = models.CharField(max_length=80, unique=True, null=True, blank=True, editable=False)
    title = models.CharField(_("title"), max_length=120, blank=True)
    context_type = models.CharField(
        _("linked to"),
        max_length=40,
        blank=True,
        help_text=_("For example a dispute, an order or a booking."),
    )
    context_id = models.UUIDField(_("linked id"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created by"),
    )
    last_message_at = models.DateTimeField(_("last message"), null=True, blank=True, db_index=True)
    payment_warning = models.BooleanField(
        _("payment warning"),
        default=False,
        help_text=_("A phone number, a payment link or a risky word was written before any order."),
    )
    is_closed = models.BooleanField(_("closed"), default=False)

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ["-last_message_at"]
        indexes = [models.Index(fields=["context_type", "context_id"])]

    def __str__(self):
        return self.title or f"{self.get_kind_display()} {str(self.pk)[:8]}"


class ConversationMember(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        REQUESTED = "requested", _("Message request")
        DECLINED = "declined", _("Request declined")
        LEFT = "left", _("Left")

    class Role(models.TextChoices):
        MEMBER = "member", _("Member")
        STAFF = "staff", _("Platform team")

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name=_("conversation"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
        verbose_name=_("person"),
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    role = models.CharField(_("role"), max_length=8, choices=Role.choices, default=Role.MEMBER)
    read_up_to = models.DateTimeField(_("read up to"), null=True, blank=True)
    delivered_up_to = models.DateTimeField(_("received up to"), null=True, blank=True)
    archived = models.BooleanField(_("archived"), default=False)
    muted = models.BooleanField(_("muted"), default=False)
    notify_scheduled = models.BooleanField(default=False, editable=False)
    last_notified_at = models.DateTimeField(null=True, blank=True, editable=False)
    away_sent_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("member")
        verbose_name_plural = _("members")
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="unique_member")
        ]

    def __str__(self):
        return f"{self.user} ({self.get_status_display()})"


class Message(BaseModel):
    class Kind(models.TextChoices):
        TEXT = "text", _("Text")
        PHOTO = "photo", _("Picture")
        VOICE = "voice", _("Voice note")
        SHARE = "share", _("Shared card")
        SYSTEM = "system", _("Information")
        CALL = "call", _("Call")

    class ShareKind(models.TextChoices):
        POST = "post", _("Post")
        PRODUCT = "product", _("Product")
        SERVICE = "service", _("Service")
        SLOT = "slot", _("Free slot")

    class Visibility(models.TextChoices):
        VISIBLE = "visible", _("Visible")
        HELD = "held", _("Held for review")
        REMOVED = "removed", _("Removed")

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("conversation"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
        verbose_name=_("sender"),
    )
    kind = models.CharField(_("type"), max_length=8, choices=Kind.choices, default=Kind.TEXT)
    text = models.TextField(_("text"), blank=True)
    media = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("file"),
    )
    share_kind = models.CharField(_("shared"), max_length=8, choices=ShareKind.choices, blank=True)
    share_id = models.UUIDField(null=True, blank=True)
    # Copy taken when sharing: the card stays readable if the original changes.
    share_data = models.JSONField(default=dict, blank=True)
    # A line of the call log (« Video call, 3 min », « Missed call »), written in her language.
    call = models.ForeignKey(
        "messaging.Call",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("call"),
    )
    # Chosen by the sending device: sending twice (offline queue) never makes two messages.
    client_id = models.UUIDField(null=True, blank=True)
    fraud_labels = models.JSONField(_("risk detected"), default=list, blank=True)
    is_automatic = models.BooleanField(_("automatic"), default=False)
    visibility = models.CharField(
        _("visibility"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "client_id"],
                condition=models.Q(client_id__isnull=False),
                name="unique_message_client_id",
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {str(self.pk)[:8]}"

    @property
    def author(self):
        """Used by the moderation app (author of the reported content)."""
        return self.sender


class QuickReply(BaseModel):
    """Saved answers of a pro (« Yes it is available », « Here are my prices »)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quick_replies",
        verbose_name=_("person"),
    )
    text = models.CharField(_("text"), max_length=500)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("quick reply")
        verbose_name_plural = _("quick replies")
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.text[:60]


class AwayMessage(BaseModel):
    """Automatic answer of a pro outside her opening hours."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="away_message",
        verbose_name=_("person"),
    )
    enabled = models.BooleanField(_("enabled"), default=False)
    text = models.CharField(_("text"), max_length=500, blank=True)

    class Meta:
        verbose_name = _("away message")
        verbose_name_plural = _("away messages")

    def __str__(self):
        return str(self.user)


class Call(BaseModel):
    """An audio or video call in a conversation (two people, or three in a dispute room).
    Nothing is recorded: only who, when and how long (the call log)."""

    class Kind(models.TextChoices):
        AUDIO = "audio", _("Audio call")
        VIDEO = "video", _("Video call")

    class Status(models.TextChoices):
        RINGING = "ringing", _("Ringing")
        ONGOING = "ongoing", _("Ongoing")
        ENDED = "ended", _("Ended")
        MISSED = "missed", _("Missed")
        DECLINED = "declined", _("Declined")
        CANCELLED = "cancelled", _("Cancelled")

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="calls", verbose_name=_("conversation")
    )
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        verbose_name=_("caller"),
    )
    kind = models.CharField(_("type"), max_length=5, choices=Kind.choices)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.RINGING, db_index=True
    )
    room = models.CharField(_("room at LiveKit"), max_length=80, unique=True)
    ring_until = models.DateTimeField(_("rings until"))
    answered_at = models.DateTimeField(_("answered at"), null=True, blank=True)
    ended_at = models.DateTimeField(_("ended at"), null=True, blank=True)
    ends_by = models.DateTimeField(_("cut at the latest"), null=True, blank=True)
    max_people = models.PositiveSmallIntegerField(_("people at most"), default=2)

    class Meta:
        verbose_name = _("call")
        verbose_name_plural = _("calls")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self) -> int:
        if self.answered_at and self.ended_at:
            return max(0, int((self.ended_at - self.answered_at).total_seconds()))
        return 0


class CallParticipant(BaseModel):
    class State(models.TextChoices):
        INVITED = "invited", _("Called")
        JOINED = "joined", _("In the call")
        LEFT = "left", _("Hung up")
        DECLINED = "declined", _("Declined")

    call = models.ForeignKey(
        Call, on_delete=models.CASCADE, related_name="participants", verbose_name=_("call")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="call_participations",
        verbose_name=_("person"),
    )
    state = models.CharField(_("state"), max_length=8, choices=State.choices, default=State.INVITED)
    joined_at = models.DateTimeField(_("joined at"), null=True, blank=True)
    left_at = models.DateTimeField(_("left at"), null=True, blank=True)

    class Meta:
        verbose_name = _("person in a call")
        verbose_name_plural = _("people in calls")
        constraints = [
            models.UniqueConstraint(fields=["call", "user"], name="messaging_one_call_participant")
        ]
