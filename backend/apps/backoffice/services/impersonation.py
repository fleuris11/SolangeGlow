"""« Sign in as » a member, for support: the team member sees the app as the person sees it.
Short (30 minutes), never on a team account, no payment, every step in the audit journal,
a banner on every page of the app."""

from __future__ import annotations

import datetime
import re

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.core.selectors import get_setting

from ..models import Impersonation

CLAIM = "imp"
BANNER_COOKIE = "sg_impersonation"
DEFAULT_BLOCKED = [
    r"^/api/v1/payments",
    r"/checkout",
    r"/pay$",
    r"/pay/",
    r"/receipt",
    r"/confirm-receipt",
    r"/wallet",
    r"/payout",
    r"^/api/v1/me/(delete|contact)",
]


class CannotImpersonate(DomainError):
    code = "cannot_impersonate"
    status_code = 403
    message = _("Signing in as this person is not allowed (team account or inactive account).")


class BlockedDuringImpersonation(DomainError):
    code = "blocked_during_impersonation"
    status_code = 403
    message = _("Not possible while signed in as a member (payments, codes, account).")


def minutes() -> int:
    return int(get_setting("backoffice.impersonation_minutes", default=30))


def can_impersonate(staff, target) -> bool:
    return (
        bool(staff and staff.is_staff)
        and (staff.is_superuser or staff.has_perm("backoffice.impersonate_user"))
        and target.is_active
        and not target.is_staff
        and not target.is_superuser
        and target.pk != staff.pk
    )


@transaction.atomic
def start(staff, target, *, reason: str) -> tuple[Impersonation, RefreshToken]:
    if not can_impersonate(staff, target):
        raise CannotImpersonate()
    Impersonation.objects.filter(staff=staff, ended_at__isnull=True).update(ended_at=timezone.now())
    found = Impersonation.objects.create(
        staff=staff,
        target=target,
        reason=(reason or "").strip()[:200],
        expires_at=timezone.now() + datetime.timedelta(minutes=minutes()),
    )
    refresh = RefreshToken.for_user(target)
    refresh[CLAIM] = str(found.pk)
    refresh.set_exp(lifetime=datetime.timedelta(minutes=minutes()))
    record(
        "backoffice.impersonation_started",
        target,
        actor=staff,
        metadata={"impersonation": str(found.pk), "reason": found.reason},
    )
    return found, refresh


def alive(impersonation_id, user_id) -> Impersonation | None:
    found = (
        Impersonation.objects.filter(pk=impersonation_id, target_id=user_id, ended_at__isnull=True)
        .select_related("staff")
        .first()
    )
    if found is None or found.expires_at <= timezone.now():
        return None
    return found


def blocked(path: str) -> bool:
    patterns = get_setting("backoffice.impersonation_blocked", default=DEFAULT_BLOCKED) or []
    return any(re.search(pattern, path) for pattern in patterns)


def note_action(impersonation: Impersonation, method: str, path: str) -> None:
    """Every change made while signed in as the member is written in the journal."""
    if path.endswith("/impersonation/stop"):
        return  # leaving is written as the end, not as an action
    Impersonation.objects.filter(pk=impersonation.pk).update(actions=F("actions") + 1)
    record(
        "backoffice.impersonation_action",
        impersonation.target,
        actor=impersonation.staff,
        metadata={"impersonation": str(impersonation.pk), "method": method, "path": path[:200]},
    )


@transaction.atomic
def stop(impersonation_id, *, user=None) -> Impersonation | None:
    found = (
        Impersonation.objects.select_for_update()
        .filter(pk=impersonation_id, ended_at__isnull=True)
        .first()
    )
    if found is None or (user is not None and found.target_id != user.pk):
        return None
    found.ended_at = timezone.now()
    found.save(update_fields=["ended_at", "updated_at"])
    record(
        "backoffice.impersonation_ended",
        found.target,
        actor=found.staff,
        metadata={"impersonation": str(found.pk), "actions": found.actions},
    )
    return found
