from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

FINANCE_GROUP = "Finance"
DISPUTES_GROUP = "Disputes"

FINANCE_PERMISSIONS = [
    "view_payment",
    "view_refund",
    "change_refund",
    "view_payout",
    "view_journalentry",
    "view_journalline",
    "view_ledgeraccount",
    "view_webhookevent",
    "view_reconciliationrun",
    "view_reconciliationitem",
    "view_pricingrule",
    "add_pricingrule",
    "change_pricingrule",
    "view_sellertaxprofile",
    "view_dispute",
]
DISPUTES_PERMISSIONS = [
    "view_payment",
    "view_dispute",
    "change_dispute",
    "view_disputeevidence",
    "decide_dispute",
]


def create_groups(sender, **kwargs):
    """« Finance » reads the money and closes refunds; « Disputes » decides the disputes
    and joins every dispute room. Members get only what their role needs."""
    from django.contrib.auth.models import Group, Permission

    for name, codenames in (
        (FINANCE_GROUP, FINANCE_PERMISSIONS),
        (DISPUTES_GROUP, DISPUTES_PERMISSIONS),
    ):
        group, _created = Group.objects.get_or_create(name=name)
        group.permissions.add(
            *Permission.objects.filter(content_type__app_label="payments", codename__in=codenames)
        )


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    verbose_name = _("Payments")

    def ready(self):
        from apps.messaging import fraud

        from .selectors import dealt_together

        post_migrate.connect(create_groups, sender=self)
        # A paid order between two people: phone numbers and links are normal now.
        fraud.register_trust_check(dealt_together)
