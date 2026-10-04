from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Channel(models.TextChoices):
    IN_APP = "in_app", _("In the app")
    EMAIL = "email", _("E-mail")
    PUSH = "push", _("Phone alert (push)")
    WHATSAPP = "whatsapp", _("WhatsApp")
    SMS = "sms", _("SMS")


class NotificationTemplate(BaseModel):
    """Text of one event on one channel, translated and editable in the admin.

    Title and body are Django templates: {{ first_name }}, {{ date }}… come from the
    context given by the module that sends the event.
    """

    event_key = models.CharField(
        _("event"), max_length=80, db_index=True, help_text=_("e.g. booking.confirmed")
    )
    channel = models.CharField(_("channel"), max_length=10, choices=Channel.choices)
    title = models.CharField(_("title"), max_length=200, blank=True)
    body = models.TextField(_("text"))
    link = models.CharField(
        _("link"), max_length=200, blank=True, help_text=_("Page opened on tap, e.g. /me")
    )
    is_active = models.BooleanField(_("active"), default=True)
    description = models.CharField(_("when is it sent?"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("notification template")
        verbose_name_plural = _("notification templates")
        ordering = ["event_key", "channel"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_key", "channel"], name="notifications_template_unique_channel"
            )
        ]

    def __str__(self):
        return f"{self.event_key} ({self.get_channel_display()})"


class Notification(BaseModel):
    """One event for one person. Shown in the app when it has an in-app text."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("person"),
    )
    event_key = models.CharField(_("event"), max_length=80, db_index=True)
    title = models.CharField(_("title"), max_length=200, blank=True)
    body = models.TextField(_("text"), blank=True)
    link = models.CharField(_("link"), max_length=200, blank=True)
    in_app = models.BooleanField(_("shown in the app"), default=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    data = models.JSONField(_("details"), default=dict, blank=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.event_key} → {self.user}"


class NotificationDelivery(BaseModel):
    """Sending of a notification on one outside channel (e-mail, push, WhatsApp, SMS)."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        SENT = "sent", _("Sent")
        SKIPPED = "skipped", _("Not sent (channel off)")
        FAILED = "failed", _("Failed")

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries"
    )
    channel = models.CharField(_("channel"), max_length=10, choices=Channel.choices)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )
    title = models.CharField(_("title"), max_length=200, blank=True)
    body = models.TextField(_("text"), blank=True)
    scheduled_for = models.DateTimeField(_("planned for"))
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    error = models.CharField(_("error"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("sending")
        verbose_name_plural = _("sendings")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel"], name="notifications_delivery_unique_channel"
            )
        ]

    def __str__(self):
        return f"{self.notification.event_key} {self.channel} {self.status}"


class PushSubscription(BaseModel):
    """A browser or installed app that accepted phone alerts (Web Push)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name=_("person"),
    )
    endpoint = models.URLField(_("address"), max_length=600, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(_("device"), max_length=255, blank=True)
    last_used_at = models.DateTimeField(_("last used"), null=True, blank=True)

    class Meta:
        verbose_name = _("push subscription")
        verbose_name_plural = _("push subscriptions")

    def __str__(self):
        return f"{self.user} {self.user_agent[:40]}"
