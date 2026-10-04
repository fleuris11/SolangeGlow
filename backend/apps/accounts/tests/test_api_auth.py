import time

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import GuestIdentity, User

from .conftest import BENIN_PHONE, CODE

pytestmark = pytest.mark.django_db

CLIENT_HEADER = {"HTTP_X_SG_CLIENT": "web"}


@pytest.fixture
def client():
    return APIClient(REMOTE_ADDR="203.0.113.9")


def sign_in(client, phone=BENIN_PHONE):
    response = client.post(reverse("v1:otp-request"), {"phone": phone}, format="json")
    assert response.status_code == 202, response.content
    challenge_id = response.json()["challenge_id"]
    response = client.post(
        reverse("v1:otp-verify"), {"challenge_id": challenge_id, "code": CODE}, format="json"
    )
    assert response.status_code in (200, 201), response.content
    return response


def test_request_code_answers_without_revealing_the_account(client, fixed_code):
    response = client.post(reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json")

    assert response.status_code == 202
    assert set(response.json()) == {"challenge_id", "channel", "resend_after", "expires_in"}


def test_request_code_requires_a_destination(client):
    response = client.post(reverse("v1:otp-request"), {}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_resend_too_soon_is_a_429_with_retry_after(client, fixed_code):
    client.post(reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json")
    response = client.post(reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json")

    assert response.status_code == 429
    assert response.json()["code"] == "resend_too_soon"
    assert int(response["Retry-After"]) > 0


def test_messages_follow_the_language_of_the_request(client, fixed_code):
    client.post(reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json")
    response = client.post(
        reverse("v1:otp-request"),
        {"phone": BENIN_PHONE},
        format="json",
        HTTP_ACCEPT_LANGUAGE="fr",
    )

    assert "code" in response.json()["message"].lower()
    assert response.json()["message"].startswith("Un code")


def test_sign_up_sets_http_only_cookies(client, fixed_code):
    response = sign_in(client)

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["user"]["onboarding_required"] is True
    for name in ("sg_access", "sg_refresh"):
        cookie = response.cookies[name]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
    assert response.cookies["sg_refresh"]["path"] == "/api/v1/auth/"
    hint = response.cookies["sg_signed_in"]
    assert hint.value == "1"
    assert not hint["httponly"]
    assert "access" not in body and "refresh" not in body


def test_wrong_code_error_tells_attempts_left(client, fixed_code):
    response = client.post(reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json")
    response = client.post(
        reverse("v1:otp-verify"),
        {"challenge_id": response.json()["challenge_id"], "code": "000000"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_code"
    assert response.json()["attempts_left"] == 4


def test_me_with_cookie(client, fixed_code):
    sign_in(client)

    response = client.get(reverse("v1:me"))

    assert response.status_code == 200
    assert response.json()["phone"] == BENIN_PHONE


def test_me_requires_authentication():
    response = APIClient().get(reverse("v1:me"))

    assert response.status_code == 401


def test_cookie_writes_need_the_client_header(client, fixed_code):
    sign_in(client)

    refused = client.patch(reverse("v1:me"), {"first_name": "Awa"}, format="json")
    accepted = client.patch(reverse("v1:me"), {"first_name": "Awa"}, format="json", **CLIENT_HEADER)

    assert refused.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["first_name"] == "Awa"


def test_bearer_header_works_for_the_future_mobile_app(client, fixed_code):
    response = sign_in(client)
    token = response.cookies["sg_access"].value

    other = APIClient()
    response = other.get(reverse("v1:me"), HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 200


def test_refresh_rotates_and_blacklists_the_old_token(client, fixed_code):
    sign_in(client)
    old_refresh = client.cookies["sg_refresh"].value

    response = client.post(reverse("v1:token-refresh"), **CLIENT_HEADER)
    assert response.status_code == 200
    new_refresh = response.cookies["sg_refresh"].value
    assert new_refresh != old_refresh

    replay = APIClient()
    replay.cookies["sg_refresh"] = old_refresh
    assert replay.post(reverse("v1:token-refresh"), **CLIENT_HEADER).status_code == 401


def test_refresh_needs_the_client_header(client, fixed_code):
    sign_in(client)

    assert client.post(reverse("v1:token-refresh")).status_code == 403


def test_logout_clears_cookies_and_blacklists_refresh(client, fixed_code):
    sign_in(client)
    refresh = client.cookies["sg_refresh"].value

    response = client.post(reverse("v1:logout"), **CLIENT_HEADER)

    assert response.status_code == 200
    assert response.cookies["sg_access"].value == ""
    replay = APIClient()
    replay.cookies["sg_refresh"] = refresh
    assert replay.post(reverse("v1:token-refresh"), **CLIENT_HEADER).status_code == 401


def test_logout_everywhere_revokes_every_token(client, fixed_code):
    sign_in(client)
    access = client.cookies["sg_access"].value
    refresh = client.cookies["sg_refresh"].value
    time.sleep(1)  # tokens are dated to the second

    response = client.post(reverse("v1:logout-all"), **CLIENT_HEADER)
    assert response.status_code == 200

    other_device = APIClient()
    assert (
        other_device.get(reverse("v1:me"), HTTP_AUTHORIZATION=f"Bearer {access}").status_code == 401
    )
    other_device.cookies["sg_refresh"] = refresh
    assert other_device.post(reverse("v1:token-refresh"), **CLIENT_HEADER).status_code == 401


def test_password_is_optional_then_usable(client, fixed_code):
    sign_in(client)
    response = client.post(
        reverse("v1:me-password"), {"password": "Gl0w-strong-pass"}, format="json", **CLIENT_HEADER
    )
    assert response.status_code == 200

    other = APIClient()
    response = other.post(
        reverse("v1:password-login"),
        {"identifier": "01 97 12 34 56", "password": "Gl0w-strong-pass"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["user"]["has_password"] is True


def test_weak_password_is_refused(client, fixed_code):
    sign_in(client)

    response = client.post(
        reverse("v1:me-password"), {"password": "123"}, format="json", **CLIENT_HEADER
    )

    assert response.status_code == 400
    assert "password" in response.json()["fields"]


def test_wrong_password_gives_one_generic_error():
    User.objects.create_user(email="awa@example.com", password="Gl0w-strong-pass")

    wrong = APIClient().post(
        reverse("v1:password-login"),
        {"identifier": "awa@example.com", "password": "nope"},
        format="json",
    )
    unknown = APIClient().post(
        reverse("v1:password-login"),
        {"identifier": "nobody@example.com", "password": "nope"},
        format="json",
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_guest_then_account_keeps_the_guest(client, fixed_code):
    response = client.post(
        reverse("v1:guest"), {"first_name": "Awa", "phone": BENIN_PHONE}, format="json"
    )
    assert response.status_code == 201
    assert client.get(reverse("v1:guest")).json()["first_name"] == "Awa"

    response = sign_in(client)

    guest = GuestIdentity.objects.get()
    assert str(guest.user_id) == response.json()["user"]["id"]
    assert response.cookies["sg_guest"].value == ""


def test_dev_code_endpoint_is_not_routed_outside_development(client):
    response = client.get("/api/v1/dev/last-code?destination=%2B2290197123456")

    assert response.status_code == 404


def test_auth_endpoints_are_in_the_openapi_schema(client):
    paths = client.get("/api/schema/", HTTP_ACCEPT="application/json").json()["paths"]

    for path in ("/api/v1/auth/otp/request", "/api/v1/auth/otp/verify", "/api/v1/me"):
        assert path in paths
