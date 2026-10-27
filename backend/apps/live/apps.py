from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.live"
    verbose_name = _("Lives")

    def ready(self):
        from apps.core.providers import livekit

        from . import services

        livekit.on_webhook(services.PREFIX, services.on_webhook)
