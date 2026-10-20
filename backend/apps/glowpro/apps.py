from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GlowProConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.glowpro"
    verbose_name = _("Glow Pro offers")

    def ready(self):
        from apps.payments import services as payment_services

        from . import services

        payment_services.listen(
            services.SOURCE, services.on_payment_change, may_cancel=services.may_cancel_payment
        )
