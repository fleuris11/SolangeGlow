from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel

from .storage import private_storage


def original_upload_to(instance, filename):
    # Originals are always private: they may still hold metadata (GPS position).
    extension = filename.rsplit(".", 1)[-1].lower()[:8] if "." in filename else "bin"
    return f"originals/{instance.kind}/{instance.pk}/original.{extension}"


class MediaAsset(BaseModel):
    """A picture, video or voice note, with its processed variants.

    Modules keep a ForeignKey to MediaAsset, never a FileField.
    """

    class Kind(models.TextChoices):
        IMAGE = "image", _("Picture")
        VIDEO = "video", _("Video")
        AUDIO = "audio", _("Voice note")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        PRIVATE = "private", _("Private (signed links)")

    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting")
        PROCESSING = "processing", _("Processing")
        READY = "ready", _("Ready")
        REJECTED = "rejected", _("Refused")
        FAILED = "failed", _("Failed")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_assets",
        verbose_name=_("owner"),
    )
    kind = models.CharField(_("type"), max_length=8, choices=Kind.choices)
    purpose = models.SlugField(_("use"), max_length=40)
    visibility = models.CharField(
        _("visibility"), max_length=8, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status = models.CharField(
        _("status"), max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    original = models.FileField(
        _("original file"), upload_to=original_upload_to, storage=private_storage, max_length=255
    )
    original_name = models.CharField(_("file name"), max_length=255, blank=True)
    content_type = models.CharField(_("content type"), max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(_("size"), default=0)
    width = models.PositiveIntegerField(_("width"), null=True, blank=True)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True)
    duration_seconds = models.FloatField(_("duration (s)"), null=True, blank=True)
    # {"thumb": {"path": "...", "width": 160, "height": 160, "bytes": 1234,
    #            "content_type": "image/webp"}, ...}
    variants = models.JSONField(_("variants"), default=dict, blank=True)
    blurhash = models.CharField(_("blur preview"), max_length=64, blank=True)
    error = models.CharField(_("error"), max_length=255, blank=True)
    processed_at = models.DateTimeField(_("processed at"), null=True, blank=True)

    class Meta:
        app_label = "core"
        verbose_name = _("media")
        verbose_name_plural = _("media")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "purpose"])]

    def __str__(self):
        return f"{self.get_kind_display()} {self.purpose} ({self.get_status_display()})"

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY
