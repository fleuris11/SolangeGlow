from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class AuditEvent(BaseModel):
    """An immutable line of the audit journal: who did what, on which object, from where."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        verbose_name=_("by"),
    )
    action = models.CharField(_("action"), max_length=80, db_index=True)
    target_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("object type"),
    )
    target_id = models.CharField(_("object id"), max_length=64, blank=True, db_index=True)
    target_repr = models.CharField(_("object"), max_length=200, blank=True)
    before = models.JSONField(_("before"), null=True, blank=True)
    after = models.JSONField(_("after"), null=True, blank=True)
    metadata = models.JSONField(_("details"), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.CharField(_("device"), max_length=255, blank=True)

    class Meta:
        app_label = "core"
        verbose_name = _("audit event")
        verbose_name_plural = _("audit journal")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.action} {self.target_repr}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Audit events are immutable.")
        super().save(*args, **kwargs)
