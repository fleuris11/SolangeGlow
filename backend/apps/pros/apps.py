from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

VERIFICATION_GROUP = "Verification"


def create_verification_group(sender, **kwargs):
    """The « verification » role: the only one who sees identity documents (ADR-005)."""
    from django.contrib.auth.models import Group, Permission

    group, _created = Group.objects.get_or_create(name=VERIFICATION_GROUP)
    permissions = Permission.objects.filter(
        content_type__app_label="pros",
        codename__in=[
            "review_identity",
            "view_proverification",
            "change_proverification",
            "view_proprofile",
        ],
    )
    group.permissions.add(*permissions)


class ProsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pros"
    verbose_name = _("Pros")

    def ready(self):
        post_migrate.connect(create_verification_group, sender=self)
