from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class BackofficeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.backoffice"
    verbose_name = _("Back office")

    def ready(self):
        from django.contrib import admin

        from apps.core import events

        from . import admin_views
        from .services import exports, prospects, team

        # A prospect who chose her password with the invitation link is signed up.
        events.subscribe("accounts.password_chosen", prospects.on_password_chosen)
        # « Remove my page » on a prepared showcase: never contacted again.
        events.subscribe("pros.prepared_removed", prospects.on_prepared_removed)

        post_migrate.connect(team.create_groups, sender=self)
        # « Export as CSV » on every list of the admin.
        admin.site.add_action(exports.export_csv, "export_csv")
        # The pages of the back office live in the admin itself (ADR-001).
        original = admin.site.get_urls

        def get_urls():
            return admin_views.urls(admin.site) + original()

        admin.site.get_urls = get_urls
