"""The live room shared by the training lives (academy) and the sales lives (shop), ADR-013.

A module plans its lives in its own model and registers a source (registry.py); the room
here holds what happens on air: broadcast, viewers, written questions, raised hands, the
recording and its replay.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class LiveRoom(BaseModel):
    class Kind(models.TextChoices):
        TRAINING = "training", _("Training live")
        SALE = "sale", _("Sales live")

    class Status(models.TextChoices):
        WAITING = "waiting", _("Not started")
        ON_AIR = "on_air", _("On air")
        ENDED = "ended", _("Over")

    class Replay(models.TextChoices):
        NONE = "none", _("No replay")
        RECORDING = "recording", _("Recording")
        PROCESSING = "processing", _("Being prepared")
        READY = "ready", _("Ready")
        FAILED = "failed", _("Failed")
        EXPIRED = "expired", _("Deleted")

    kind = models.CharField(_("type"), max_length=10, choices=Kind.choices)
    source_id = models.UUIDField(_("planned live"))
    name = models.CharField(_("room at LiveKit"), max_length=80, unique=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("host"),
    )
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="live_rooms",
        verbose_name=_("pro"),
        help_text=_("Empty: a live of the platform."),
    )
    country = models.ForeignKey(
        "core.Country", on_delete=models.PROTECT, related_name="+", verbose_name=_("country")
    )
    title = models.CharField(_("title"), max_length=120)
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.WAITING
    )
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    ended_at = models.DateTimeField(_("ended at"), null=True, blank=True)
    ends_by = models.DateTimeField(
        _("cut at the latest"),
        null=True,
        blank=True,
        help_text=_("Start + the longest length allowed (setting live.max_minutes)."),
    )
    max_viewers = models.PositiveIntegerField(_("places"), default=0)
    viewers = models.PositiveIntegerField(_("watching now"), default=0)
    peak_viewers = models.PositiveIntegerField(_("most at the same time"), default=0)
    total_viewers = models.PositiveIntegerField(_("people who came"), default=0)
    speaker_identity = models.CharField(_("has the floor"), max_length=60, blank=True)
    ended_by_staff = models.BooleanField(_("cut by the team"), default=False)
    egress_id = models.CharField(max_length=80, blank=True, editable=False)
    replay_status = models.CharField(
        _("replay"), max_length=10, choices=Replay.choices, default=Replay.NONE
    )
    replay = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("replay video"),
    )
    replay_until = models.DateTimeField(_("replay visible until"), null=True, blank=True)

    class Meta:
        verbose_name = _("live room")
        verbose_name_plural = _("live rooms")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "source_id"], name="live_one_room_per_live")
        ]
        indexes = [models.Index(fields=["status", "ends_by"])]

    def __str__(self):
        return self.title


class LiveQuestion(BaseModel):
    """A written question (or a comment during a sale). Moderated like any content."""

    class Visibility(models.TextChoices):
        VISIBLE = "visible", _("Visible")
        HELD = "held", _("Held for review")
        REMOVED = "removed", _("Removed")

    room = models.ForeignKey(
        LiveRoom, on_delete=models.CASCADE, related_name="questions", verbose_name=_("live")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("author"),
    )
    text = models.CharField(_("question"), max_length=300)
    at_second = models.PositiveIntegerField(
        _("second of the live"), default=0, help_text=_("Places it in the replay.")
    )
    answered_at = models.DateTimeField(_("answered"), null=True, blank=True)
    visibility = models.CharField(
        _("visibility"), max_length=8, choices=Visibility.choices, default=Visibility.VISIBLE
    )

    class Meta:
        verbose_name = _("question in a live")
        verbose_name_plural = _("questions in the lives")
        ordering = ["created_at"]

    def __str__(self):
        return self.text[:60]


class LiveHand(BaseModel):
    """« Raise my hand »: the host gives the floor (her microphone opens) and takes it back."""

    class Status(models.TextChoices):
        RAISED = "raised", _("Hand raised")
        SPEAKING = "speaking", _("Has the floor")
        DONE = "done", _("Done")

    room = models.ForeignKey(
        LiveRoom, on_delete=models.CASCADE, related_name="hands", verbose_name=_("live")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("person"),
    )
    status = models.CharField(_("status"), max_length=8, choices=Status.choices)
    raised_at = models.DateTimeField(_("raised at"))

    class Meta:
        verbose_name = _("raised hand")
        verbose_name_plural = _("raised hands")
        ordering = ["raised_at"]
        constraints = [models.UniqueConstraint(fields=["room", "user"], name="live_one_hand")]


class LiveAttendance(BaseModel):
    """Who came and when (from the webhooks of LiveKit): numbers of the live, never shown
    to other viewers."""

    room = models.ForeignKey(
        LiveRoom, on_delete=models.CASCADE, related_name="attendance", verbose_name=_("live")
    )
    identity = models.CharField(_("identity"), max_length=60)
    joined_at = models.DateTimeField(_("came in"))
    left_at = models.DateTimeField(_("left"), null=True, blank=True)

    class Meta:
        verbose_name = _("presence")
        verbose_name_plural = _("presences")
        indexes = [models.Index(fields=["room", "identity"])]
