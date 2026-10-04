import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser(
        email="owner@example.com", password="s3cret-pass"
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize(
    "url_name",
    [
        "admin:index",
        "admin:core_country_changelist",
        "admin:core_currency_changelist",
        "admin:core_platformsetting_changelist",
        "admin:core_platformsetting_add",
        "admin:core_featureflag_changelist",
        "admin:core_featureflag_add",
        "admin:accounts_user_changelist",
        "admin:accounts_user_add",
        "admin:django_celery_beat_periodictask_add",
    ],
)
def test_admin_pages_render(admin_client, url_name):
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200


def test_admin_title(admin_client):
    response = admin_client.get(reverse("admin:index"))

    assert "Solange Glow" in response.content.decode()


def test_admin_can_create_user_with_phone_only(admin_client):
    response = admin_client.post(
        reverse("admin:accounts_user_add"),
        {
            "email": "",
            "phone": "+33612345678",
            "roles": ["client", "pro"],
            "usable_password": "true",
            "password1": "Gl0w-strong-pass",
            "password2": "Gl0w-strong-pass",
        },
    )

    assert response.status_code == 302, response.content.decode()[:2000]
    user = get_user_model().objects.get(phone="+33612345678")
    assert user.email is None
    assert user.roles == ["client", "pro"]
    assert user.check_password("Gl0w-strong-pass")
