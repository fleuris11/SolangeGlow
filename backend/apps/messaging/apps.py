from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MessagingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.messaging"
    verbose_name = _("Messaging")

    def ready(self):
        from apps.core.providers import livekit

        from . import calls

        livekit.on_webhook(calls.PREFIX, calls.on_webhook)
