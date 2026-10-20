from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SalonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.salon"
    verbose_name = _("Salon management")

    def ready(self):
        from apps.booking.services import common as booking
        from apps.payments import services as payment_services

        from .services import giftcards, packages, stock

        payment_services.listen(
            packages.SOURCE, packages.on_payment_change, may_cancel=packages.may_cancel_payment
        )
        payment_services.listen(
            giftcards.SOURCE, giftcards.on_payment_change, may_cancel=giftcards.may_cancel_payment
        )
        booking.on_completed(packages.on_completed)
        booking.on_completed(stock.on_completed)
        booking.deposit_cover(giftcards.cover_deposit)
