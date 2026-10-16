from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

TEAM_PERMISSIONS = [
    "view_selectionproduct",
    "add_selectionproduct",
    "change_selectionproduct",
    "view_selectioncategory",
    "view_selectionorder",
    "change_selectionorder",
    "view_shipment",
    "add_shipment",
    "change_shipment",
    "view_specialrequest",
    "change_specialrequest",
    "view_groupbuy",
    "add_groupbuy",
    "change_groupbuy",
    "view_pickuppoint",
]


def create_group(sender, **kwargs):
    """« Selection France » buys at the merchants, ships the batches and quotes requests."""
    from django.contrib.auth.models import Group, Permission

    from .services import TEAM_GROUP

    group, _created = Group.objects.get_or_create(name=TEAM_GROUP)
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="selection_france", codename__in=TEAM_PERMISSIONS
        )
    )


class SelectionFranceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.selection_france"
    verbose_name = _("France Selection")

    def ready(self):
        from apps.payments import services as payment_services

        from . import services

        post_migrate.connect(create_group, sender=self)
        payment_services.listen(
            services.SOURCE, services.on_payment_change, may_cancel=services.may_cancel
        )
