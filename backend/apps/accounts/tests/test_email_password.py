"""The classic sign-up: e-mail and password, a link confirms the address, « forgot password »,
a pause after too many wrong passwords, and the phone number asked at the welcome screen."""

import re
from smtplib import SMTPDataError
from urllib.parse import unquote

import pytest
from celery.exceptions import Retry
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import errors, services, tasks
from apps.accounts.models import SignupChannel, User
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Rose-Hibiscus-2026"
ADULT_BIRTH_DATE = "1995-04-12"


@pytest.fixture(autouse=True)
def fresh_cache():
    cache.clear()


@pytest.fixture
def client():
    # Writes signed in by cookie carry the app's header (protection against other sites).
    return APIClient(REMOTE_ADDR="203.0.113.20", HTTP_X_SG_CLIENT="web")


def token_in(message) -> str:
    found = re.search(r"token=(\S+)", message.body)
    assert found, message.body
    return unquote(found.group(1))


def sign_up(client, email="awa@example.com", password=PASSWORD, first_name="Awa"):
    return client.post(
        reverse("v1:signup"),
        {"email": email, "password": password, "first_name": first_name, "locale": "fr"},
        format="json",
    )


def test_sign_up_sends_a_confirmation_link_then_the_link_signs_in(client, settings):
    settings.SITE_URL = "https://solangeglow.com"
    answer = sign_up(client, email="Awa@Example.com")
    assert answer.status_code == 202 and answer.json() == {"sent_to": "aw***@example.com"}
    user = User.objects.get(email="awa@example.com")
    assert user.email_verified_at is None and user.check_password(PASSWORD)
    assert user.first_name == "Awa" and user.preferred_language == "fr"
    [message] = mail.outbox
    assert message.to == ["awa@example.com"]
    assert "https://solangeglow.com/fr/auth/confirm?token=" in message.body

    # Not confirmed yet: the right password sends a new link instead of a session.
    refused = client.post(
        reverse("v1:password-login"),
        {"identifier": "awa@example.com", "password": PASSWORD},
        format="json",
    )
    assert refused.status_code == 403 and refused.json()["code"] == "email_not_confirmed"
    assert len(mail.outbox) == 2

    confirmed = client.post(
        reverse("v1:email-confirm"), {"token": token_in(mail.outbox[0])}, format="json"
    )
    assert confirmed.status_code == 201, confirmed.content
    assert confirmed.json()["user"]["onboarding_required"] is True
    assert "sg_access" in confirmed.cookies
    user.refresh_from_db()
    assert user.email_verified_at is not None

    # A link works once: used again, it no longer signs in.
    again = client.post(
        reverse("v1:email-confirm"), {"token": token_in(mail.outbox[1])}, format="json"
    )
    assert again.status_code == 400 and again.json()["code"] == "invalid_link"

    signed_in = APIClient().post(
        reverse("v1:password-login"),
        {"identifier": "AWA@example.com", "password": PASSWORD},
        format="json",
    )
    assert signed_in.status_code == 200 and signed_in.json()["user"]["first_name"] == "Awa"


def test_a_weak_password_is_refused_with_the_reason(client):
    answer = sign_up(client, password="12345678")
    assert answer.status_code == 400
    body = answer.json()
    assert body["code"] == "weak_password" and body["fields"]["password"]
    assert not User.objects.exists() and not mail.outbox


def test_an_address_with_an_account_gets_an_e_mail_not_a_second_account(client):
    existing = User.objects.create_user(email="awa@example.com", password=PASSWORD)
    existing.email_verified_at = existing.created_at
    existing.save()
    answer = sign_up(client, password="Autre-Mot-De-Passe-77")
    # Same answer as a new address: nobody learns who is registered.
    assert answer.status_code == 202 and answer.json() == {"sent_to": "aw***@example.com"}
    assert User.objects.count() == 1
    existing.refresh_from_db()
    assert existing.check_password(PASSWORD)  # unchanged
    [message] = mail.outbox
    assert "/fr/auth/reset?token=" in message.body


def test_signing_up_again_before_confirming_replaces_the_password(client):
    sign_up(client, password="Premier-Essai-2026")
    sign_up(client, password=PASSWORD, first_name="Awa D.")
    user = User.objects.get()
    assert user.check_password(PASSWORD) and user.first_name == "Awa D."
    assert len(mail.outbox) == 2
    # The first link no longer works: the second one does.
    assert (
        client.post(
            reverse("v1:email-confirm"), {"token": token_in(mail.outbox[1])}, format="json"
        ).status_code
        == 201
    )


def test_resend_answers_the_same_for_any_address(client):
    sign_up(client)
    mail.outbox.clear()
    for address in ("awa@example.com", "nobody@example.com"):
        answer = client.post(reverse("v1:email-resend"), {"email": address}, format="json")
        assert answer.status_code == 202
    assert [m.to for m in mail.outbox] == [["awa@example.com"]]


def test_forgot_password_then_a_new_one_signs_in_and_closes_other_sessions(client):
    sign_up(client)
    client.post(reverse("v1:email-confirm"), {"token": token_in(mail.outbox[0])}, format="json")
    user = User.objects.get()
    mail.outbox.clear()

    for address in ("awa@example.com", "nobody@example.com"):
        answer = client.post(reverse("v1:password-forgot"), {"email": address}, format="json")
        assert answer.status_code == 202
    [message] = mail.outbox
    assert "/fr/auth/reset?token=" in message.body
    token = token_in(message)

    weak = client.post(
        reverse("v1:password-reset"), {"token": token, "password": "azerty"}, format="json"
    )
    assert weak.status_code == 400 and weak.json()["code"] == "weak_password"
    done = client.post(
        reverse("v1:password-reset"),
        {"token": token, "password": "Nouveau-Mot-De-Passe-9"},
        format="json",
    )
    assert done.status_code == 200 and "sg_access" in done.cookies
    user.refresh_from_db()
    assert user.check_password("Nouveau-Mot-De-Passe-9") and user.tokens_revoked_at
    # Used once: the same link no longer works.
    again = client.post(
        reverse("v1:password-reset"),
        {"token": token, "password": "Encore-Un-Autre-5"},
        format="json",
    )
    assert again.status_code == 400 and again.json()["code"] == "invalid_link"


def test_a_reset_link_also_proves_the_address_of_an_unconfirmed_account(client):
    sign_up(client)
    mail.outbox.clear()
    client.post(reverse("v1:password-forgot"), {"email": "awa@example.com"}, format="json")
    client.post(
        reverse("v1:password-reset"),
        {"token": token_in(mail.outbox[0]), "password": "Nouveau-Mot-De-Passe-9"},
        format="json",
    )
    assert User.objects.get().email_verified_at is not None


def test_links_expire(client):
    PlatformSettingFactory(key="accounts.email_link_hours", value="-1")
    sign_up(client)
    answer = client.post(
        reverse("v1:email-confirm"), {"token": token_in(mail.outbox[0])}, format="json"
    )
    assert answer.status_code == 400 and answer.json()["code"] == "invalid_link"
    assert (
        client.post(reverse("v1:email-confirm"), {"token": "made-up"}, format="json").status_code
        == 400
    )


def test_too_many_wrong_passwords_pause_the_address(client):
    PlatformSettingFactory(key="accounts.password_max_failures", value="3")
    sign_up(client)
    client.post(reverse("v1:email-confirm"), {"token": token_in(mail.outbox[0])}, format="json")
    login = reverse("v1:password-login")
    for _ in range(3):
        wrong = client.post(
            login, {"identifier": "awa@example.com", "password": "pas-le-bon"}, format="json"
        )
        assert wrong.status_code == 401 and wrong.json()["code"] == "invalid_credentials"
    locked = client.post(
        login, {"identifier": "awa@example.com", "password": PASSWORD}, format="json"
    )
    assert locked.status_code == 429 and locked.json()["code"] == "password_locked"
    assert "15" in locked.json()["message"]
    # « Forgot password » stays open, and a new password lifts the pause.
    mail.outbox.clear()
    client.post(reverse("v1:password-forgot"), {"email": "awa@example.com"}, format="json")
    client.post(
        reverse("v1:password-reset"),
        {"token": token_in(mail.outbox[0]), "password": "Nouveau-Mot-De-Passe-9"},
        format="json",
    )
    assert (
        client.post(
            login,
            {"identifier": "awa@example.com", "password": "Nouveau-Mot-De-Passe-9"},
            format="json",
        ).status_code
        == 200
    )


def test_the_e_mail_is_tried_again_when_the_service_refuses(monkeypatch):
    user = User.objects.create_user(email="awa@example.com", password=PASSWORD)

    def refused(*args, **kwargs):
        raise SMTPDataError(502, b"5.7.0 Your SMTP account is not yet activated")

    monkeypatch.setattr("django.core.mail.send_mail", refused)
    with pytest.raises(Retry):
        tasks.send_account_link.apply(args=(str(user.pk), "confirm"))
    assert (
        tasks.send_account_link.apply(args=(str(user.pk), "confirm"), retries=4).result == "failed"
    )
    assert services.deliver_link(str(user.pk), "unknown") == "skipped"


def test_the_welcome_screen_asks_for_a_phone_number(client):
    CountryFactory(code="BJ", is_active=True)
    sign_up(client)
    client.post(reverse("v1:email-confirm"), {"token": token_in(mail.outbox[0])}, format="json")
    onboarding = reverse("v1:me-onboarding")
    base = {"mode": "client", "birth_date": ADULT_BIRTH_DATE, "accept_terms": True}
    missing = client.post(onboarding, base, format="json")
    assert missing.status_code == 400 and missing.json()["code"] == "phone_needed"
    wrong = client.post(onboarding, {**base, "phone": "123"}, format="json")
    assert wrong.status_code == 400 and wrong.json()["code"] == "invalid_destination"
    User.objects.create_user(phone="+2290197000001")
    taken = client.post(onboarding, {**base, "phone": "+229 01 97 00 00 01"}, format="json")
    assert taken.status_code == 400 and taken.json()["code"] == "contact_taken"
    done = client.post(onboarding, {**base, "phone": "+229 01 97 12 34 56"}, format="json")
    assert done.status_code == 200, done.content
    user = User.objects.get(email="awa@example.com")
    assert str(user.phone) == "+2290197123456" and user.phone_verified_at is None
    assert user.country.code == "BJ"


def test_a_number_only_typed_never_opens_that_account_by_code(fixed_code):
    from apps.accounts.tests.conftest import CODE

    typed = User.objects.create_user(
        email="awa@example.com",
        phone="+2290197123456",
        password=PASSWORD,
        signup_channel=SignupChannel.EMAIL,
    )
    challenge = services.request_code(phone="+2290197123456")
    result = services.verify_code(challenge_id=challenge.challenge_id, code=CODE)
    assert result.created and result.user.pk != typed.pk
    typed.refresh_from_db()
    assert typed.phone is None


def test_errors_say_what_to_do():
    assert "15" in errors.PasswordLocked(details={"minutes": 15}).text()
