from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts import errors, services
from apps.accounts.models import GuestIdentity, LoginEvent, OtpChallenge, SignupChannel, User
from apps.core.models import PlatformSetting
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory

from .conftest import BENIN_PHONE, CODE, FRANCE_PHONE

pytestmark = pytest.mark.django_db


def request(**kwargs):
    kwargs.setdefault("ip", "203.0.113.7")
    return services.request_code(**kwargs)


# --- Request -------------------------------------------------------------------------


def test_code_is_sent_on_whatsapp_first(senders, fixed_code):
    result = request(phone="01 97 12 34 56 ", locale="fr")

    assert result.channel == "whatsapp"
    message = senders["whatsapp"].sent[0]
    assert message.destination == BENIN_PHONE
    assert message.code == CODE
    assert message.locale == "fr"
    assert not senders["sms"].sent


def test_the_code_is_stored_hashed_only(senders, fixed_code):
    result = request(phone=BENIN_PHONE)

    challenge = OtpChallenge.objects.get(pk=result.challenge_id)
    assert CODE not in challenge.code_hash
    assert BENIN_PHONE not in challenge.destination_hash
    assert challenge.country_code == "BJ"


def test_sms_is_the_fallback_when_whatsapp_fails(senders, fixed_code):
    senders["whatsapp"].fails = True

    result = request(phone=BENIN_PHONE)

    assert result.channel == "sms"
    assert senders["sms"].sent[0].code == CODE


def test_unconfigured_channel_is_skipped(senders):
    senders["whatsapp"].available = False

    assert request(phone=BENIN_PHONE).channel == "sms"


def test_channel_order_comes_from_platform_settings(senders):
    PlatformSettingFactory(
        key="otp.phone_channels",
        value_type=PlatformSetting.ValueType.JSON,
        value='["sms", "whatsapp"]',
    )

    assert request(phone=BENIN_PHONE).channel == "sms"


def test_channel_order_can_differ_per_country(senders):
    PlatformSettingFactory(
        key="otp.phone_channels",
        value_type=PlatformSetting.ValueType.JSON,
        value='["sms"]',
        country=CountryFactory(code="FR", phone_prefix="+33"),
    )

    assert request(phone=FRANCE_PHONE).channel == "sms"
    assert request(phone=BENIN_PHONE).channel == "whatsapp"


def test_delivery_failure_on_every_channel(senders):
    senders["whatsapp"].fails = True
    senders["sms"].fails = True

    with pytest.raises(errors.DeliveryFailed):
        request(phone=BENIN_PHONE)


def test_email_goes_through_the_email_channel(senders):
    result = request(email="  Awa@Example.com ")

    assert result.channel == "email"
    assert senders["email"].sent[0].destination == "awa@example.com"


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"phone": "12"}, {"email": "not-an-email"}, {"phone": BENIN_PHONE, "email": "a@b.co"}],
)
def test_invalid_destinations_are_refused(senders, kwargs):
    with pytest.raises(errors.InvalidDestination):
        request(**kwargs)


def test_resend_is_blocked_during_the_cooldown(senders):
    request(phone=BENIN_PHONE)

    with pytest.raises(errors.ResendTooSoon) as excinfo:
        request(phone=BENIN_PHONE)
    assert 0 < excinfo.value.details["retry_after"] <= 60


def test_limit_per_destination_per_hour(senders):
    PlatformSettingFactory(key="otp.resend_cooldown_seconds", value="0")
    PlatformSettingFactory(key="otp.max_requests_per_destination_per_hour", value="2")
    request(phone=BENIN_PHONE)
    request(phone=BENIN_PHONE)

    with pytest.raises(errors.TooManyRequests):
        request(phone=BENIN_PHONE)


def test_limit_per_ip_per_hour(senders):
    PlatformSettingFactory(key="otp.max_requests_per_ip_per_hour", value="2")
    request(phone=BENIN_PHONE, ip="198.51.100.1")
    request(phone=FRANCE_PHONE, ip="198.51.100.1")

    with pytest.raises(errors.TooManyRequests):
        request(email="awa@example.com", ip="198.51.100.1")
    assert request(email="awa@example.com", ip="198.51.100.2").channel == "email"


def test_same_answer_whether_the_account_exists_or_not(senders):
    User.objects.create_user(phone=BENIN_PHONE)

    existing = request(phone=BENIN_PHONE)
    unknown = request(phone=FRANCE_PHONE)

    assert existing.channel == unknown.channel
    assert existing.resend_after == unknown.resend_after
    assert existing.expires_in == unknown.expires_in


# --- Verify --------------------------------------------------------------------------


def test_right_code_creates_the_account(senders, fixed_code):
    CountryFactory(code="BJ")
    challenge_id = request(phone=BENIN_PHONE).challenge_id

    result = services.verify_code(challenge_id=challenge_id, code=CODE, locale="en")

    user = result.user
    assert result.created is True
    assert str(user.phone) == BENIN_PHONE
    assert user.signup_channel == SignupChannel.PHONE
    assert user.phone_verified_at is not None
    assert user.preferred_language == "en"
    assert user.country.code == "BJ"
    assert user.preferred_currency.code == "XOF"
    assert not user.has_usable_password()
    assert LoginEvent.objects.filter(user=user, success=True, channel="whatsapp").exists()


def test_right_code_signs_in_an_existing_account(senders, fixed_code):
    existing = User.objects.create_user(email="awa@example.com")
    challenge_id = request(email="AWA@example.com").challenge_id

    result = services.verify_code(challenge_id=challenge_id, code=CODE)

    assert result.created is False
    assert result.user == existing
    assert User.objects.count() == 1


def test_wrong_code_counts_an_attempt(senders, fixed_code):
    challenge_id = request(phone=BENIN_PHONE).challenge_id

    with pytest.raises(errors.InvalidCode) as excinfo:
        services.verify_code(challenge_id=challenge_id, code="000000")

    assert excinfo.value.details["attempts_left"] == 4
    assert OtpChallenge.objects.get(pk=challenge_id).attempts == 1
    assert LoginEvent.objects.filter(success=False, failure_reason="invalid_code").count() == 1
    assert not User.objects.exists()


def test_too_many_wrong_codes_locks_the_code(senders, fixed_code):
    PlatformSettingFactory(key="otp.max_attempts", value="2")
    challenge_id = request(phone=BENIN_PHONE).challenge_id

    with pytest.raises(errors.InvalidCode):
        services.verify_code(challenge_id=challenge_id, code="000000")
    with pytest.raises(errors.TooManyAttempts):
        services.verify_code(challenge_id=challenge_id, code="111111")
    # Even the right code is refused now.
    with pytest.raises(errors.TooManyAttempts):
        services.verify_code(challenge_id=challenge_id, code=CODE)


def test_expired_code_is_refused(senders, fixed_code):
    challenge_id = request(phone=BENIN_PHONE).challenge_id
    OtpChallenge.objects.filter(pk=challenge_id).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    with pytest.raises(errors.CodeExpired):
        services.verify_code(challenge_id=challenge_id, code=CODE)


def test_code_cannot_be_used_twice(senders, fixed_code):
    challenge_id = request(phone=BENIN_PHONE).challenge_id
    services.verify_code(challenge_id=challenge_id, code=CODE)

    with pytest.raises(errors.ChallengeNotFound):
        services.verify_code(challenge_id=challenge_id, code=CODE)


@pytest.mark.parametrize("challenge_id", ["not-a-uuid", "6f1c1d1e-0000-4000-8000-000000000000"])
def test_unknown_challenge(challenge_id):
    with pytest.raises(errors.ChallengeNotFound):
        services.verify_code(challenge_id=challenge_id, code=CODE)


def test_suspended_account_cannot_sign_in(senders, fixed_code):
    User.objects.create_user(phone=BENIN_PHONE, is_active=False)
    challenge_id = request(phone=BENIN_PHONE).challenge_id

    with pytest.raises(errors.AccountSuspended):
        services.verify_code(challenge_id=challenge_id, code=CODE)


def test_guest_identity_is_attached_on_sign_up(senders, fixed_code):
    guest = services.create_guest(first_name="Awa", phone="01 97 12 34 56")
    challenge_id = request(phone=BENIN_PHONE).challenge_id

    user = services.verify_code(challenge_id=challenge_id, code=CODE, guest_id=str(guest.pk)).user

    guest.refresh_from_db()
    assert guest.user == user
    assert guest.converted_at is not None


def test_attach_guest_ignores_unknown_or_taken_guests():
    user = User.objects.create_user(email="a@example.com")
    other = User.objects.create_user(email="b@example.com")
    taken = GuestIdentity.objects.create(first_name="Awa", phone=BENIN_PHONE, user=other)

    assert services.attach_guest(user, "not-a-uuid") == 0
    assert services.attach_guest(user, str(taken.pk)) == 0
