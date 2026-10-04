from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SelectionFranceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.selection_france"
    verbose_name = _("France Selection")
