from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

REVIEW_GROUP = "Academy review"
REVIEW_PERMISSIONS = [
    "view_course",
    "change_course",
    "review_course",
    "view_coursereview",
    "change_coursereview",
    "view_enrollment",
    "view_certificate",
    "change_certificate",
    "view_livesession",
    "view_liveroom",
    "change_liveroom",
    "view_livequestion",
    "change_livequestion",
]


def create_group(sender, **kwargs):
    """« Academy review » reads the courses of the pros before they are published."""
    from django.contrib.auth.models import Group, Permission

    group, _created = Group.objects.get_or_create(name=REVIEW_GROUP)
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label__in=["academy", "live"], codename__in=REVIEW_PERMISSIONS
        )
    )


class AcademyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.academy"
    verbose_name = _("Academy")

    def ready(self):
        from apps.live import registry
        from apps.payments import services as payment_services

        from .live_source import TrainingLives
        from .services import common, enrollments, passes

        post_migrate.connect(create_group, sender=self)
        registry.register(TrainingLives())

        payment_services.listen(
            common.SOURCE, enrollments.on_payment_change, may_cancel=enrollments.may_cancel_payment
        )
        payment_services.listen(
            common.PASS_SOURCE, passes.on_payment_change, may_cancel=passes.may_cancel_payment
        )
