from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GamificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gamification"
    verbose_name = _("Games")

    def ready(self):
        from apps.booking.services import common as booking
        from apps.core import events

        from .services import hooks

        events.subscribe("social.post_published", hooks.on_post_published)
        events.subscribe("social.review_created", hooks.on_review_created)
        events.subscribe("payments.moved", hooks.on_payment_moved)
        booking.on_completed(hooks.on_appointment_completed)
