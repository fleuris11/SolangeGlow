import datetime
import io

import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import GuestIdentity, User
from apps.core.choices import Role
from apps.core.media.models import MediaAsset
from apps.core.tests.factories import CountryFactory, CurrencyFactory, PlatformSettingFactory
from apps.pros.models import ProProfile

pytestmark = pytest.mark.django_db

CLIENT_HEADER = {"HTTP_X_SG_CLIENT": "web"}
ADULT_BIRTH_DATE = "1995-04-12"


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


def years_ago(years: int, days: int = 0) -> str:
    today = timezone.localdate()
    return (today.replace(year=today.year - years) - datetime.timedelta(days=days)).isoformat()


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
            "quiet_hours_start": "21:30",
            "quiet_hours_end": "06:00",
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
    assert user.quiet_hours_start == datetime.time(21, 30)
    assert response.json()["quiet_hours_end"] == "06:00"


def test_identifiers_birth_date_and_roles_are_read_only(client, user):
    client.patch(
        reverse("v1:me"),
        {
            "email": "x@example.com",
            "phone": "+33612345678",
            "roles": ["staff"],
            "birth_date": "2015-01-01",
        },
        format="json",
    )

    user.refresh_from_db()
    assert user.email is None
    assert str(user.phone) == "+2290197123456"
    assert user.roles == [Role.CLIENT]
    assert user.birth_date is None


# --- Welcome screens, age ------------------------------------------------------------


def test_onboarding_as_pro_with_trades(client, user):
    response = client.post(
        reverse("v1:me-onboarding"),
        {
            "mode": "pro",
            "birth_date": ADULT_BIRTH_DATE,
            "trades": ["braids", "makeup"],
            "language": "fr",
            "city": "Cotonou",
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["is_pro"] is True
    assert body["is_minor"] is False
    assert body["onboarding_required"] is False
    profile = ProProfile.objects.get(user=user)
    assert set(profile.trades.values_list("key", flat=True)) == {"braids", "makeup"}


def test_onboarding_needs_a_birth_date(client):
    response = client.post(reverse("v1:me-onboarding"), {"mode": "client"}, format="json")

    assert response.status_code == 400
    assert "birth_date" in response.json()["fields"]


def test_onboarding_as_pro_needs_a_trade(client):
    response = client.post(
        reverse("v1:me-onboarding"),
        {"mode": "pro", "birth_date": ADULT_BIRTH_DATE},
        format="json",
    )

    assert response.status_code == 400
    assert "trades" in response.json()["fields"]


def test_onboarding_refuses_people_under_the_minimum_age(client, user):
    response = client.post(
        reverse("v1:me-onboarding"),
        {"mode": "client", "birth_date": years_ago(16, days=-1)},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "too_young"
    user.refresh_from_db()
    assert user.onboarded_at is None


def test_minimum_age_is_a_setting(client):
    PlatformSettingFactory(key="accounts.minimum_age", value="13")

    response = client.post(
        reverse("v1:me-onboarding"), {"mode": "client", "birth_date": years_ago(14)}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["is_minor"] is True


def test_birth_date_in_the_future_is_refused(client):
    tomorrow = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()

    response = client.post(
        reverse("v1:me-onboarding"), {"mode": "client", "birth_date": tomorrow}, format="json"
    )

    assert response.json()["code"] == "invalid_birth_date"


def test_onboarding_as_client(client, user):
    response = client.post(
        reverse("v1:me-onboarding"),
        {"mode": "client", "birth_date": ADULT_BIRTH_DATE, "city": "Paris"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["is_pro"] is False
    assert not ProProfile.objects.exists()


# --- Catalogue -----------------------------------------------------------------------


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


# --- Photo ---------------------------------------------------------------------------


def test_photo_goes_through_the_media_pipeline(client, user):
    upload = SimpleUploadedFile("me.jpg", jpeg_with_gps(), content_type="image/jpeg")

    response = client.post(reverse("v1:me-photo"), {"photo": upload}, format="multipart")

    assert response.status_code == 202, response.content
    user.refresh_from_db()
    asset = user.photo
    assert asset.purpose == "avatar"
    assert asset.status == MediaAsset.Status.READY  # Celery runs at once in tests
    assert set(asset.variants) == {"thumb", "medium", "large"}
    assert asset.blurhash
    public = storages["media_public"]
    with public.open(asset.variants["large"]["path"], "rb") as stored:
        image = Image.open(stored)
        assert image.format == "WEBP"
        assert max(image.size) == 1200  # never enlarged
        assert not image.getexif()


def test_non_image_upload_is_refused(client, user):
    upload = SimpleUploadedFile("me.jpg", b"%PDF-1.4 not an image", content_type="image/jpeg")

    client.post(reverse("v1:me-photo"), {"photo": upload}, format="multipart")

    user.refresh_from_db()
    assert user.photo.status == MediaAsset.Status.REJECTED
    response = client.get(reverse("v1:me"))
    assert response.json()["photo"]["status"] == "rejected"
    assert response.json()["photo"]["urls"] == {}


def test_photo_can_be_replaced_and_removed(client, user):
    first = SimpleUploadedFile("a.jpg", jpeg_with_gps(), content_type="image/jpeg")
    second = SimpleUploadedFile("b.jpg", jpeg_with_gps(), content_type="image/jpeg")
    client.post(reverse("v1:me-photo"), {"photo": first}, format="multipart")
    client.post(reverse("v1:me-photo"), {"photo": second}, format="multipart")

    assert MediaAsset.objects.count() == 1  # the old photo is deleted

    response = client.delete(reverse("v1:me-photo"))

    assert response.json()["photo"] is None
    assert not MediaAsset.objects.exists()


# --- Deletion with grace period ------------------------------------------------------


def test_account_deletion_needs_confirmation(client, user):
    response = client.delete(reverse("v1:me"), {"confirm": False}, format="json")

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.deletion_requested_at is None


def test_deletion_is_scheduled_after_the_grace_period(client, user):
    response = client.delete(reverse("v1:me"), {"confirm": True}, format="json")

    assert response.status_code == 202
    user.refresh_from_db()
    assert user.deletion_requested_at is not None
    assert user.phone is not None  # nothing erased yet
    erase_after = datetime.datetime.fromisoformat(response.json()["erase_after"])
    assert (erase_after - user.deletion_requested_at).days == 30
    assert user.tokens_revoked_at is not None


def test_purge_erases_personal_data_after_the_grace_period(user):
    from apps.accounts import services
    from apps.accounts.tasks import purge_deleted_accounts

    GuestIdentity.objects.create(first_name="Awa", phone="+2290197123456", user=user)
    services.request_deletion(user)
    assert purge_deleted_accounts() == 0  # still in the grace period

    User.objects.filter(pk=user.pk).update(
        deletion_requested_at=timezone.now() - datetime.timedelta(days=31)
    )
    assert purge_deleted_accounts() == 1

    user.refresh_from_db()
    assert user.phone is None
    assert user.first_name == ""
    assert user.email.endswith("@deleted.invalid")
    assert not user.is_active
    assert user.deleted_at is not None
    assert not GuestIdentity.objects.exists()
    assert User.objects.create_user(phone="+2290197123456")  # the number is free again
