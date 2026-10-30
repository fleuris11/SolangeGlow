"""Security of the back office: two-factor sign-in of every team account, the permissions
of each role, « sign in as » a member always traced and limited."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.backoffice.models import Impersonation, RecoveryCode, StaffDevice
from apps.backoffice.services import impersonation, team, twofactor
from apps.core.audit.models import AuditEvent
from apps.messaging.tests.factories import adult

pytestmark = pytest.mark.django_db
User = get_user_model()
H = {"HTTP_X_SG_CLIENT": "web"}


def owner():
    return User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")


def member(*roles, email="team@example.com"):
    return team.save_member(
        email=email, first_name="Équipe", password="t3am-pass", roles=list(roles), actor=None
    )


# --- Two-factor ----------------------------------------------------------------------------------


@pytest.fixture
def two_factor_on(settings):
    settings.BACKOFFICE_REQUIRE_2FA = True


def current_code(user, *, shift=0) -> str:
    secret = twofactor.secret_of(StaffDevice.objects.get(user=user))
    return twofactor.code_at(secret, twofactor.current_step() + shift)


def test_every_team_account_must_pass_two_factor(client, two_factor_on):
    boss = owner()
    client.force_login(boss)
    blocked = client.get(reverse("admin:index"))
    assert blocked.status_code == 302
    assert blocked["Location"].startswith(reverse("admin:backoffice_2fa"))
    setup = client.get(reverse("admin:backoffice_2fa"))
    assert setup.status_code == 200
    assert "<svg" in setup.content.decode()  # the square to scan
    wrong = client.post(reverse("admin:backoffice_2fa"), {"code": "000000"})
    assert wrong.status_code == 200
    assert client.get(reverse("admin:index")).status_code == 302
    passed = client.post(reverse("admin:backoffice_2fa"), {"code": current_code(boss)})
    assert passed.status_code == 200  # the backup codes, shown once
    assert RecoveryCode.objects.filter(user=boss).count() == 10
    assert client.get(reverse("admin:index")).status_code == 200
    assert AuditEvent.objects.filter(action="backoffice.two_factor_enabled").exists()


def test_a_code_never_works_twice_and_tries_are_limited(two_factor_on):
    boss = owner()
    twofactor.device_of(boss)
    code = current_code(boss)
    assert twofactor.verify(boss, code) is True
    assert twofactor.verify(boss, code) is False  # replayed
    assert twofactor.verify(boss, current_code(boss, shift=1)) is True  # the next one, once
    for _ in range(5):
        twofactor.verify(boss, "123456")
    assert twofactor.verify(boss, current_code(boss, shift=1)) is False  # locked for a while


def test_a_backup_code_opens_once(client, two_factor_on):
    boss = owner()
    twofactor.device_of(boss)
    twofactor.verify(boss, current_code(boss))
    codes = twofactor.new_recovery_codes(boss)
    client.force_login(boss)
    client.post(reverse("admin:backoffice_2fa"), {"backup": codes[0]})
    assert client.get(reverse("admin:index")).status_code == 200
    assert twofactor.use_recovery_code(boss, codes[0]) is False
    assert twofactor.use_recovery_code(boss, codes[1]) is True


def test_members_of_the_app_are_not_concerned(client, two_factor_on):
    client.force_login(adult())
    assert client.get("/api/v1/me").status_code == 200


# --- Roles ---------------------------------------------------------------------------------------

PAGES = {
    "moderation": "admin:backoffice_moderation_console",
    "disputes": "admin:backoffice_disputes_console",
    "selection": "admin:backoffice_selection_console",
    "team": "admin:backoffice_team",
    "flags": "admin:backoffice_flags",
    "translations": "admin:backoffice_translations",
}
ALLOWED = {
    "moderation": {"moderation"},
    "disputes": {"disputes"},
    "selection": {"selection"},
    "support": set(),
    "ads": set(),
    "finance": set(),
    "verification": set(),
}


@pytest.mark.parametrize("role", sorted(ALLOWED))
def test_each_role_opens_only_its_consoles(client, role):
    team.create_groups()
    client.force_login(member(role))
    for page, name in PAGES.items():
        expected = 200 if page in ALLOWED[role] else 403
        assert client.get(reverse(name)).status_code == expected, (role, page)


def test_role_lists_in_the_admin(client):
    team.create_groups()
    client.force_login(member("ads"))
    assert client.get(reverse("admin:ads_campaign_changelist")).status_code == 200
    assert client.get(reverse("admin:payments_payment_changelist")).status_code == 403
    client.force_login(member("finance", email="finance@example.com"))
    assert client.get(reverse("admin:payments_payment_changelist")).status_code == 200
    assert client.get(reverse("admin:ads_campaign_changelist")).status_code == 403


def test_the_owner_opens_everything_and_manages_the_team(client):
    team.create_groups()
    boss = owner()
    client.force_login(boss)
    for name in PAGES.values():
        assert client.get(reverse(name)).status_code == 200
    client.post(
        reverse("admin:backoffice_team"),
        {"email": "awa.team@example.com", "first_name": "Awa", "roles": ["support"]},
    )
    created = User.objects.get(email="awa.team@example.com")
    assert created.is_staff and team.roles_of(created) == ["support"]
    client.post(reverse("admin:backoffice_team"), {"action": "remove", "user": created.pk})
    created.refresh_from_db()
    assert not created.is_staff


# --- Sign in as ----------------------------------------------------------------------------------


def test_sign_in_as_a_member_is_traced_and_shown(client):
    boss = owner()
    awa = adult()
    client.force_login(boss)
    url = reverse("admin:backoffice_impersonate", args=[awa.pk])
    assert client.get(url).status_code == 200
    response = client.post(url, {"reason": "Ticket T-ABC123"})
    assert response.status_code == 302
    assert response.cookies["sg_access"].value
    assert response.cookies[impersonation.BANNER_COOKIE].value.endswith("|Awa")
    found = Impersonation.objects.get()
    assert (found.staff, found.target, found.reason) == (boss, awa, "Ticket T-ABC123")
    assert AuditEvent.objects.filter(action="backoffice.impersonation_started").exists()

    app = APIClient()
    app.cookies["sg_access"] = response.cookies["sg_access"].value
    me = app.get("/api/v1/me")
    assert me.status_code == 200 and me.json()["first_name"] == "Awa"
    changed = app.patch("/api/v1/me", {"first_name": "Awa Z"}, format="json", **H)
    assert changed.status_code == 200
    action = AuditEvent.objects.get(action="backoffice.impersonation_action")
    assert action.actor == boss and action.metadata["method"] == "PATCH"

    blocked = app.post("/api/v1/payments/whatever/confirm-receipt", {}, format="json", **H)
    assert blocked.status_code in (403, 404)
    assert impersonation.blocked("/api/v1/payments/123/confirm-receipt")

    stopped = app.post("/api/v1/backoffice/impersonation/stop", **H)
    assert stopped.status_code == 204
    found.refresh_from_db()
    assert found.ended_at is not None and found.actions == 1
    assert AuditEvent.objects.filter(action="backoffice.impersonation_ended").exists()
    assert app.get("/api/v1/me").status_code == 401


def test_sign_in_as_ends_by_itself():
    boss = owner()
    awa = adult()
    found, refresh = impersonation.start(boss, awa, reason="Aide")
    assert impersonation.alive(found.pk, awa.pk) is not None
    Impersonation.objects.filter(pk=found.pk).update(
        expires_at=timezone.now() - datetime.timedelta(minutes=1)
    )
    assert impersonation.alive(found.pk, awa.pk) is None
    app = APIClient()
    app.cookies["sg_access"] = str(refresh.access_token)
    assert app.get("/api/v1/me").status_code == 401


def test_never_on_a_team_account_nor_without_the_right(client):
    boss = owner()
    colleague = member("support")
    with pytest.raises(impersonation.CannotImpersonate):
        impersonation.start(boss, colleague, reason="x")
    team.create_groups()
    moderator = member("moderation", email="mod@example.com")
    client.force_login(moderator)
    assert client.get(reverse("admin:backoffice_impersonate", args=[adult().pk])).status_code == 403
    support = member("support", email="support@example.com")
    assert impersonation.can_impersonate(support, adult("Fifamè"))
