from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class BackofficeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.backoffice"
    verbose_name = _("Back office")

    def ready(self):
        from django.contrib import admin

        from . import admin_views
        from .services import exports, team

        post_migrate.connect(team.create_groups, sender=self)
        # « Export as CSV » on every list of the admin.
        admin.site.add_action(exports.export_csv, "export_csv")
        # The pages of the back office live in the admin itself (ADR-001).
        original = admin.site.get_urls

        def get_urls():
            return admin_views.urls(admin.site) + original()

        admin.site.get_urls = get_urls
