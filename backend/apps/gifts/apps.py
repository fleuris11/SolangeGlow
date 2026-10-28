from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GiftsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gifts"
    verbose_name = _("Gifts")

    def ready(self):
        from apps.booking.services import common as booking
        from apps.payments import services as payment_services
        from apps.payments.providers import gift as gift_provider

        from . import services
        from .services import common

        payment_services.listen(
            common.SOURCE, services.on_payment_change, may_cancel=services.may_cancel_payment
        )
        gift_provider.on_refund(services.credit_back)
        booking.on_completed(services.on_completed)
        booking.deposit_cover(services.cover_deposit)
