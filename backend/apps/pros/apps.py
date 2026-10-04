from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pros"
    verbose_name = _("Pros")
