from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Reason(models.TextChoices):
    SPAM = "spam", _("Spam or advertising")
    NUDITY = "nudity", _("Nudity or sexual content")
    HARASSMENT = "harassment", _("Harassment or insults")
    HATE = "hate", _("Hate or discrimination")
    SCAM = "scam", _("Scam or fraud")
    MINOR = "minor", _("Danger for a minor")
    VIOLENCE = "violence", _("Violence")
    OTHER = "other", _("Something else")


class TargetMixin(models.Model):
    """Any content: post, comment, story, review or a person."""

    target_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+", verbose_name=_("content type")
    )
    target_id = models.UUIDField(_("content"))
    target = GenericForeignKey("target_type", "target_id")

    class Meta:
        abstract = True


class Report(TargetMixin, BaseModel):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_made",
        verbose_name=_("reported by"),
    )
    reason = models.CharField(_("reason"), max_length=12, choices=Reason.choices)
    comment = models.CharField(_("details"), max_length=500, blank=True)
    case = models.ForeignKey(
        "ModerationCase",
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("case"),
    )

    class Meta:
        verbose_name = _("report")
        verbose_name_plural = _("reports")
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"], name="moderation_report_once"
            )
        ]

    def __str__(self):
        return f"{self.get_reason_display()} ({self.target_type.model})"


class Block(BaseModel):
    """She no longer sees him, he no longer sees her, and neither can reach the other."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )

    class Meta:
        verbose_name = _("block")
        verbose_name_plural = _("blocks")
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="moderation_block_once")
        ]

    def __str__(self):
        return f"{self.blocker} / {self.blocked}"


class Hide(TargetMixin, BaseModel):
    """A content (or all the posts of a person) she does not want to see any more."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hidden_items"
    )

    class Meta:
        verbose_name = _("hidden content")
        verbose_name_plural = _("hidden contents")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target_type", "target_id"], name="moderation_hide_once"
            )
        ]

    def __str__(self):
        return f"{self.user} / {self.target_type.model}"


class ModerationCase(TargetMixin, BaseModel):
    """One content in the moderation queue, with the reports and the automatic check."""

    class Status(models.TextChoices):
        PENDING = "pending", _("To review")
        KEPT = "kept", _("Kept")
        REMOVED = "removed", _("Removed")

    class Source(models.TextChoices):
        REPORT = "report", _("Reported")
        AUTOMATIC = "automatic", _("Automatic check")

    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    source = models.CharField(_("found by"), max_length=10, choices=Source.choices)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="moderation_cases",
        verbose_name=_("author"),
    )
    excerpt = models.TextField(_("excerpt"), blank=True)
    labels = models.JSONField(_("detected"), default=list, blank=True)
    provider = models.CharField(_("checked by"), max_length=20, blank=True)
    hidden_until_review = models.BooleanField(_("hidden until review"), default=False)
    report_count = models.PositiveIntegerField(_("reports"), default=0)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("decided by"),
    )
    decided_at = models.DateTimeField(_("decided at"), null=True, blank=True)
    note = models.TextField(_("note"), blank=True)

    class Meta:
        verbose_name = _("moderation case")
        verbose_name_plural = _("moderation queue")
        ordering = ["status", "-report_count", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["target_type", "target_id"],
                condition=models.Q(status="pending"),
                name="moderation_one_open_case",
            )
        ]

    def __str__(self):
        return f"{self.target_type.model} {self.excerpt[:40]}"


class Sanction(BaseModel):
    """Graduated sanctions: warning, then no posting, then suspension, then ban."""

    class Level(models.TextChoices):
        WARNING = "warning", _("Warning")
        MUTE = "mute", _("Cannot post or comment")
        SUSPENSION = "suspension", _("Suspended")
        BAN = "ban", _("Banned")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sanctions",
        verbose_name=_("person"),
    )
    level = models.CharField(_("level"), max_length=10, choices=Level.choices)
    until = models.DateTimeField(_("until"), null=True, blank=True)
    reason = models.TextField(_("reason"), blank=True)
    case = models.ForeignKey(
        ModerationCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sanctions",
        verbose_name=_("case"),
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("sanction")
        verbose_name_plural = _("sanctions")
        ordering = ["-created_at"]
