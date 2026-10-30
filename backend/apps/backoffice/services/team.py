"""The team of the owner: roles (groups with only the permissions they need), team members
created from the admin, CSV exports traced."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.audit.services import record

# role key -> (group name, label, [(app_label, codename)])
ROLES: dict[str, tuple[str, str, list[tuple[str, str]]]] = {
    "moderation": (
        "Moderation",
        _("Moderation"),
        [
            ("backoffice", "use_moderation_console"),
            ("moderation", "view_moderationcase"),
            ("moderation", "change_moderationcase"),
            ("moderation", "view_report"),
            ("moderation", "view_sanction"),
            ("moderation", "add_sanction"),
            ("social", "view_post"),
            ("social", "view_comment"),
            ("social", "view_review"),
            ("gamification", "view_poll"),
            ("gamification", "change_poll"),
            ("gamification", "view_challengeentry"),
        ],
    ),
    "support": (
        "Support",
        _("Support"),
        [
            ("backoffice", "view_dashboard"),
            ("backoffice", "impersonate_user"),
            ("accounts", "view_user"),
            ("content", "view_ticket"),
            ("content", "change_ticket"),
            ("content", "view_faqitem"),
            ("shop", "view_order"),
            ("booking", "view_appointment"),
            ("payments", "view_payment"),
        ],
    ),
    "disputes": (
        "Disputes",
        _("Disputes"),
        [
            ("backoffice", "use_disputes_console"),
            ("payments", "view_payment"),
            ("payments", "view_dispute"),
            ("payments", "change_dispute"),
            ("payments", "view_disputeevidence"),
            ("payments", "decide_dispute"),
            ("messaging", "view_conversation"),
        ],
    ),
    "ads": (
        "Ads",
        _("Advertising"),
        [
            ("ads", "view_advertiser"),
            ("ads", "add_advertiser"),
            ("ads", "change_advertiser"),
            ("ads", "view_campaign"),
            ("ads", "add_campaign"),
            ("ads", "change_campaign"),
            ("ads", "view_creative"),
            ("ads", "add_creative"),
            ("ads", "change_creative"),
            ("ads", "view_adstat"),
            ("ads", "view_boost"),
            ("backoffice", "export_csv"),
        ],
    ),
    "finance": (
        "Finance",
        _("Finance"),
        [
            ("backoffice", "view_dashboard"),
            ("backoffice", "export_csv"),
            ("payments", "view_payment"),
            ("payments", "view_refund"),
            ("payments", "change_refund"),
            ("payments", "view_payout"),
            ("payments", "view_journalentry"),
            ("payments", "view_journalline"),
            ("payments", "view_ledgeraccount"),
            ("payments", "view_pricingrule"),
            ("payments", "view_dispute"),
        ],
    ),
    "verification": (
        "Verification",
        _("Pro verification"),
        [
            ("pros", "view_proprofile"),
            ("pros", "view_proverification"),
            ("pros", "change_proverification"),
            ("pros", "review_identity"),
            ("backoffice", "view_prospect"),
            ("backoffice", "change_prospect"),
        ],
    ),
    "selection": (
        "Selection",
        _("France Selection"),
        [
            ("backoffice", "use_selection_console"),
            ("selection_france", "view_selectionorder"),
            ("selection_france", "change_selectionorder"),
            ("selection_france", "view_shipment"),
            ("selection_france", "add_shipment"),
            ("selection_france", "change_shipment"),
            ("selection_france", "view_selectionproduct"),
            ("selection_france", "view_specialrequest"),
            ("selection_france", "change_specialrequest"),
        ],
    ),
}


def create_groups(sender=None, **kwargs) -> None:
    """Every role and its permissions (added, never removed: the owner can add more)."""
    for _key, (name, _label, perms) in ROLES.items():
        group, _created = Group.objects.get_or_create(name=name)
        found = []
        for app_label, codename in perms:
            perm = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if perm is not None:
                found.append(perm)
        group.permissions.add(*found)


def roles_of(user) -> list[str]:
    names = set(user.groups.values_list("name", flat=True))
    return [key for key, (name, _label, _perms) in ROLES.items() if name in names]


@transaction.atomic
def save_member(*, email: str, first_name: str, password: str, roles: list[str], actor):
    """A team member: staff account, her roles; she sets up two-factor at her first sign-in."""
    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    created = user is None
    if created:
        user = User.objects.create_user(email=email, first_name=first_name)
    user.first_name = first_name or user.first_name
    user.is_staff = True
    if password:
        user.set_password(password)
    user.save()
    names = [ROLES[key][0] for key in roles if key in ROLES]
    user.groups.remove(*Group.objects.filter(name__in=[r[0] for r in ROLES.values()]))
    user.groups.add(*Group.objects.filter(name__in=names))
    record(
        "backoffice.member_saved",
        user,
        actor=actor,
        metadata={"roles": roles, "created": created},
    )
    return user


@transaction.atomic
def remove_member(user, *, actor) -> None:
    user.is_staff = False
    user.save(update_fields=["is_staff", "updated_at"])
    user.groups.clear()
    record("backoffice.member_removed", user, actor=actor)
