from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ads"
    verbose_name = _("Advertising")

    def ready(self):
        from apps.booking.services import common as booking
        from apps.core import events
        from apps.payments import services as payment_services

        from .services import boosts, hooks

        payment_services.listen(
            boosts.SOURCE, boosts.on_payment_change, may_cancel=boosts.may_cancel_payment
        )
        events.subscribe("payments.moved", hooks.on_payment_moved)
        booking.on_completed(hooks.on_appointment_completed)
