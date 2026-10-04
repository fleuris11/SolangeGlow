import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.core.choices import Role

pytestmark = pytest.mark.django_db

User = get_user_model()

BENIN_PHONE = "+229 01 97 12 34 56"
BENIN_PHONE_E164 = "+2290197123456"
FRANCE_PHONE_E164 = "+33612345678"


def test_custom_user_model_is_active():
    assert User._meta.label == "accounts.User"


def test_create_user_with_email_only():
    user = User.objects.create_user(email="Awa@Example.COM", password="s3cret-pass")

    assert user.email == "awa@example.com"
    assert user.phone is None
    assert user.check_password("s3cret-pass")
    assert user.roles == [Role.CLIENT]
    assert user.preferred_language == "fr"


def test_create_user_with_phone_only_is_stored_in_e164():
    user = User.objects.create_user(phone=BENIN_PHONE)

    user.refresh_from_db()
    assert user.email is None
    assert str(user.phone) == BENIN_PHONE_E164
    assert not user.has_usable_password()


def test_phone_or_email_is_required():
    with pytest.raises(ValueError):
        User.objects.create_user()
    with pytest.raises(ValueError):
        User.objects.create_user(email="", phone="")


def test_model_validation_requires_phone_or_email():
    user = User(email="", phone="")
    with pytest.raises(ValidationError):
        user.full_clean(exclude=["password"])


def test_database_rejects_user_without_identifier():
    with pytest.raises(IntegrityError):
        User.objects.bulk_create([User(email=None, phone=None, password="!")])


def test_invalid_phone_is_rejected():
    with pytest.raises(ValidationError):
        User.objects.create_user(phone="12345")


def test_email_is_unique_case_insensitive():
    User.objects.create_user(email="fifi@example.com")

    with pytest.raises(ValidationError):
        User.objects.create_user(email="FIFI@example.com")
    with pytest.raises(IntegrityError):
        User.objects.bulk_create([User(email="fifi@example.com", password="!")])


def test_phone_is_unique():
    User.objects.create_user(phone=FRANCE_PHONE_E164)

    with pytest.raises(ValidationError):
        User.objects.create_user(phone="+33 6 12 34 56 78")


def test_several_users_without_email_or_without_phone_can_coexist():
    User.objects.create_user(phone=FRANCE_PHONE_E164)
    User.objects.create_user(phone=BENIN_PHONE)
    User.objects.create_user(email="a@example.com")
    User.objects.create_user(email="b@example.com")

    assert User.objects.count() == 4


def test_create_superuser_has_admin_access():
    admin = User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")

    assert admin.is_staff
    assert admin.is_superuser
    assert admin.has_role(Role.STAFF)


@pytest.mark.parametrize("identifier", ["owner@example.com", "OWNER@example.com"])
def test_authenticate_with_email(identifier):
    user = User.objects.create_user(email="owner@example.com", password="s3cret-pass")

    assert authenticate(username=identifier, password="s3cret-pass") == user
    assert authenticate(username=identifier, password="wrong") is None


@pytest.mark.parametrize("identifier", [BENIN_PHONE, BENIN_PHONE_E164, "0197123456"])
def test_authenticate_with_phone(identifier):
    user = User.objects.create_user(phone=BENIN_PHONE, password="s3cret-pass")

    assert authenticate(username=identifier, password="s3cret-pass") == user


def test_inactive_user_cannot_authenticate():
    User.objects.create_user(email="off@example.com", password="s3cret-pass", is_active=False)

    assert authenticate(username="off@example.com", password="s3cret-pass") is None


def test_display_preferences_have_comfortable_defaults():
    user = User.objects.create_user(email="prefs@example.com")

    assert user.theme == "system"
    assert user.text_size == "normal"
    assert user.data_saver is False
    assert user.audio_mode is False


def test_display_preferences_are_validated():
    user = User.objects.create_user(email="prefs@example.com")
    user.text_size = "huge"

    with pytest.raises(ValidationError):
        user.full_clean(exclude=["password"])
