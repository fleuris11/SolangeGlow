import datetime

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import errors, selectors, services
from apps.accounts.models import OtpChallenge, User
from apps.core.audit.models import AuditEvent
from apps.notifications.models import Notification

from .conftest import BENIN_PHONE, CODE, FRANCE_PHONE

pytestmark = pytest.mark.django_db


@pytest.fixture
def awa():
    return User.objects.create_user(phone=BENIN_PHONE, first_name="Awa")


@pytest.fixture
def client(awa):
    api = APIClient()
    api.force_authenticate(awa)
    return api


def years_ago(years: int) -> datetime.date:
    today = timezone.localdate()
    return today.replace(year=today.year - years)


# --- Change of number or e-mail ------------------------------------------------------


def test_add_an_email_with_a_code_sent_to_it(client, awa, senders, fixed_code):
    response = client.post(reverse("v1:me-contact"), {"email": "Awa@Example.com"}, format="json")
    assert response.status_code == 202
    assert senders["email"].sent[0].destination == "awa@example.com"

    response = client.post(
        reverse("v1:me-contact-confirm"),
        {"challenge_id": response.json()["challenge_id"], "code": CODE},
        format="json",
    )

    assert response.status_code == 200
    awa.refresh_from_db()
    assert awa.email == "awa@example.com"
    assert awa.email_verified_at is not None
    assert AuditEvent.objects.filter(action="account.contact_changed").exists()
    assert Notification.objects.filter(user=awa, event_key="account.contact_changed").exists()


def test_change_the_number(client, awa, senders, fixed_code):
    challenge_id = client.post(
        reverse("v1:me-contact"), {"phone": FRANCE_PHONE}, format="json"
    ).json()["challenge_id"]
    client.post(
        reverse("v1:me-contact-confirm"),
        {"challenge_id": challenge_id, "code": CODE},
        format="json",
    )

    awa.refresh_from_db()
    assert str(awa.phone) == FRANCE_PHONE


def test_contact_already_used_or_identical_is_refused(awa, senders):
    User.objects.create_user(email="taken@example.com")

    with pytest.raises(errors.ContactTaken):
        services.request_contact_change(awa, email="TAKEN@example.com")
    with pytest.raises(errors.SameContact):
        services.request_contact_change(awa, phone="01 97 12 34 56")


def test_wrong_code_does_not_change_anything(client, awa, senders, fixed_code):
    challenge_id = client.post(
        reverse("v1:me-contact"), {"email": "new@example.com"}, format="json"
    ).json()["challenge_id"]

    response = client.post(
        reverse("v1:me-contact-confirm"),
        {"challenge_id": challenge_id, "code": "000000"},
        format="json",
    )

    assert response.json()["code"] == "invalid_code"
    awa.refresh_from_db()
    assert awa.email is None


def test_a_change_code_cannot_sign_in_and_belongs_to_one_account(awa, senders, fixed_code):
    result = services.request_contact_change(awa, email="new@example.com")

    with pytest.raises(errors.ChallengeNotFound):
        services.verify_code(challenge_id=result.challenge_id, code=CODE)
    other = User.objects.create_user(email="other@example.com")
    with pytest.raises(errors.ChallengeNotFound):
        services.confirm_contact_change(other, challenge_id=result.challenge_id, code=CODE)
    assert OtpChallenge.objects.get(pk=result.challenge_id).purpose == "change_contact"


# --- Sign-in and deletion grace period -----------------------------------------------


def test_signing_in_during_the_grace_period_keeps_the_account(awa, senders, fixed_code):
    services.request_deletion(awa)
    challenge_id = services.request_code(phone=BENIN_PHONE).challenge_id

    result = services.verify_code(challenge_id=challenge_id, code=CODE)

    assert result.deletion_cancelled is True
    awa.refresh_from_db()
    assert awa.deletion_requested_at is None
    assert AuditEvent.objects.filter(action="account.deletion_cancelled").exists()


def test_sign_in_api_reports_the_cancelled_deletion(awa, senders, fixed_code):
    services.request_deletion(awa)
    api = APIClient()
    challenge_id = api.post(
        reverse("v1:otp-request"), {"phone": BENIN_PHONE}, format="json"
    ).json()["challenge_id"]

    response = api.post(
        reverse("v1:otp-verify"), {"challenge_id": challenge_id, "code": CODE}, format="json"
    )

    assert response.json()["deletion_cancelled"] is True


def test_new_account_gets_the_welcome_notification(senders, fixed_code):
    challenge_id = services.request_code(phone=BENIN_PHONE).challenge_id

    user = services.verify_code(challenge_id=challenge_id, code=CODE).user

    assert Notification.objects.filter(user=user, event_key="account.welcome").exists()


# --- Minors --------------------------------------------------------------------------


def test_minor_rules_come_from_settings(awa):
    from apps.core.tests.factories import PlatformSettingFactory

    awa.birth_date = years_ago(17)
    stranger = User.objects.create_user(email="s@example.com")

    assert selectors.is_minor(awa)
    assert not selectors.can_purchase(awa)
    assert not selectors.can_receive_message_from(awa, stranger)
    assert selectors.can_receive_message_from(awa, stranger, sender_is_followed=True)

    PlatformSettingFactory(key="accounts.minors_can_purchase", value_type="boolean", value="true")
    assert selectors.can_purchase(awa)

    awa.birth_date = years_ago(25)
    assert not selectors.is_minor(awa)
    assert selectors.can_receive_message_from(awa, stranger)


def test_unknown_birth_date_is_treated_as_minor(awa):
    assert selectors.is_minor(awa)


def test_pending_deletion_hides_the_person(awa):
    assert selectors.is_visible(awa)
    services.request_deletion(awa)
    assert not selectors.is_visible(awa)


# --- Demo data -----------------------------------------------------------------------


def test_seed_demo_is_for_development_only():
    with pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)


def test_seed_demo_creates_realistic_people_once():
    call_command("seed_demo", "--force", verbosity=0)
    count = User.objects.count()

    call_command("seed_demo", "--force", verbosity=0)

    assert User.objects.count() == count >= 11
    aicha = User.objects.get(first_name="Aïcha")
    assert aicha.is_pro if hasattr(aicha, "is_pro") else "pro" in aicha.roles
    assert aicha.pro_profile.trades.filter(key="braids").exists()
    assert aicha.country.code == "BJ"
    assert User.objects.filter(country__code="FR").exists()
    assert Notification.objects.filter(event_key="account.welcome").count() == count
