import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import GuestIdentity, User
from apps.core.choices import Role
from apps.core.tests.factories import CountryFactory, CurrencyFactory
from apps.pros.models import ProProfile

pytestmark = pytest.mark.django_db

CLIENT_HEADER = {"HTTP_X_SG_CLIENT": "web"}


@pytest.fixture
def user():
    return User.objects.create_user(phone="+2290197123456", first_name="Awa")


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


def jpeg_with_gps() -> bytes:
    image = Image.new("RGB", (1200, 800), (200, 16, 46))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    gps = exif.get_ifd(0x8825)
    gps[2] = (6.0, 21.0, 0.0)  # latitude of Cotonou
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def test_profile_update(client, user):
    CountryFactory(code="FR", phone_prefix="+33", default_currency=CurrencyFactory(code="EUR"))

    response = client.patch(
        reverse("v1:me"),
        {
            "first_name": "Awa",
            "last_name": "Dossou",
            "city": "Abomey-Calavi",
            "country": "FR",
            "preferred_currency": "EUR",
            "preferred_language": "en",
            "theme": "dark",
            "text_size": "xlarge",
            "audio_mode": True,
            "notify_whatsapp": False,
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    user.refresh_from_db()
    assert user.city == "Abomey-Calavi"
    assert user.country.code == "FR"
    assert user.preferred_currency.code == "EUR"
    assert user.text_size == "xlarge"
    assert user.notify_whatsapp is False


def test_identifiers_and_roles_are_read_only(client, user):
    client.patch(reverse("v1:me"), {"email": "x@example.com", "roles": ["staff"]}, format="json")

    user.refresh_from_db()
    assert user.email is None
    assert user.roles == [Role.CLIENT]


def test_onboarding_as_pro_with_trades(client, user):
    response = client.post(
        reverse("v1:me-onboarding"),
        {"mode": "pro", "trades": ["braids", "makeup"], "language": "fr", "city": "Cotonou"},
        format="json",
    )

    assert response.status_code == 200, response.content
    assert response.json()["is_pro"] is True
    assert response.json()["onboarding_required"] is False
    profile = ProProfile.objects.get(user=user)
    assert set(profile.trades.values_list("key", flat=True)) == {"braids", "makeup"}


def test_onboarding_as_pro_needs_a_trade(client):
    response = client.post(reverse("v1:me-onboarding"), {"mode": "pro"}, format="json")

    assert response.status_code == 400
    assert "trades" in response.json()["fields"]


def test_onboarding_as_client(client, user):
    response = client.post(
        reverse("v1:me-onboarding"), {"mode": "client", "city": "Paris"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["is_pro"] is False
    assert not ProProfile.objects.exists()


def test_trades_are_public_and_translated():
    response = APIClient().get(reverse("v1:trades"), HTTP_ACCEPT_LANGUAGE="en")

    assert response.status_code == 200
    names = {trade["key"]: trade["name"] for trade in response.json()}
    assert names["braids"] == "Braids"
    assert len(names) == 7


def test_countries_are_public():
    CountryFactory(code="BJ")

    response = APIClient().get(reverse("v1:countries"))

    assert response.json()[0] == {
        "code": "BJ",
        "name": "Bénin",
        "phone_prefix": "+229",
        "default_currency": "XOF",
    }


def test_avatar_is_reencoded_without_metadata(client, user):
    upload = SimpleUploadedFile("me.jpg", jpeg_with_gps(), content_type="image/jpeg")

    response = client.post(reverse("v1:me-avatar"), {"photo": upload}, format="multipart")

    assert response.status_code == 200, response.content
    user.refresh_from_db()
    assert response.json()["avatar_url"].endswith(".webp")
    with user.avatar.open("rb") as stored:
        image = Image.open(stored)
        assert image.format == "WEBP"
        assert image.size == (512, 512)
        assert not image.getexif()
        assert "exif" not in image.info


def test_non_image_upload_is_refused(client):
    upload = SimpleUploadedFile("me.jpg", b"%PDF-1.4 not an image", content_type="image/jpeg")

    response = client.post(reverse("v1:me-avatar"), {"photo": upload}, format="multipart")

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_image"


def test_avatar_can_be_removed(client, user):
    upload = SimpleUploadedFile("me.jpg", jpeg_with_gps(), content_type="image/jpeg")
    client.post(reverse("v1:me-avatar"), {"photo": upload}, format="multipart")

    response = client.delete(reverse("v1:me-avatar"))

    assert response.json()["avatar_url"] is None


def test_account_deletion_needs_confirmation(client, user):
    response = client.delete(reverse("v1:me"), {"confirm": False}, format="json")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.is_active


def test_account_deletion_erases_personal_data(client, user):
    GuestIdentity.objects.create(first_name="Awa", phone="+2290197123456", user=user)

    response = client.delete(reverse("v1:me"), {"confirm": True}, format="json")

    assert response.status_code == 204
    user.refresh_from_db()
    assert user.phone is None
    assert user.first_name == ""
    assert user.email.endswith("@deleted.invalid")
    assert not user.is_active
    assert user.deleted_at is not None
    assert not GuestIdentity.objects.exists()
    # The number is free again for a new account.
    assert User.objects.create_user(phone="+2290197123456")
