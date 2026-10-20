from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BookingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.booking"
    verbose_name = _("Booking")

    def ready(self):
        from apps.payments import services as payment_services
        from apps.social import eligibility

        from .links import BookingEligibility
        from .services import appointments

        payment_services.listen(
            appointments.SOURCE,
            appointments.on_payment_change,
            may_cancel=appointments.may_cancel_payment,
        )
        eligibility.register(BookingEligibility())
