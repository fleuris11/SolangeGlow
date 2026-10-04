import pytest
from django.urls import reverse

from apps.accounts import services
from apps.accounts.models import LoginEvent, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")


@pytest.fixture
def admin_client(client, owner):
    client.force_login(owner)
    return client


def test_suspend_then_reactivate_from_the_admin(admin_client, owner):
    awa = User.objects.create_user(phone="+2290197123456")
    url = reverse("admin:accounts_user_changelist")

    admin_client.post(url, {"action": "suspend_users", "_selected_action": [awa.pk, owner.pk]})
    awa.refresh_from_db()
    owner.refresh_from_db()
    assert awa.is_active is False
    assert awa.tokens_revoked_at is not None
    assert owner.is_active is True  # nobody suspends themselves

    admin_client.post(url, {"action": "reactivate_users", "_selected_action": [awa.pk]})
    awa.refresh_from_db()
    assert awa.is_active is True


def test_deleted_accounts_are_not_reactivated(admin_client):
    awa = User.objects.create_user(phone="+2290197123456")
    services.anonymize_account(awa)

    admin_client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "reactivate_users", "_selected_action": [awa.pk]},
    )

    awa.refresh_from_db()
    assert awa.is_active is False


@pytest.mark.parametrize(
    "query",
    ["role=pro", "status=suspended", "signup_channel__exact=phone", "country__id__exact=1"],
)
def test_user_filters(admin_client, query):
    response = admin_client.get(reverse("admin:accounts_user_changelist") + "?" + query)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "url_name",
    [
        "admin:accounts_loginevent_changelist",
        "admin:accounts_otpchallenge_changelist",
        "admin:accounts_guestidentity_changelist",
        "admin:pros_trade_changelist",
        "admin:pros_proprofile_changelist",
    ],
)
def test_account_admin_pages_render(admin_client, url_name):
    assert admin_client.get(reverse(url_name)).status_code == 200


def test_login_journal_appears_on_the_user_page(admin_client):
    awa = User.objects.create_user(phone="+2290197123456")
    LoginEvent.objects.create(user=awa, method="otp", channel="whatsapp", success=True)

    response = admin_client.get(reverse("admin:accounts_user_change", args=[awa.pk]))

    assert response.status_code == 200
    assert "whatsapp" in response.content.decode().lower()
