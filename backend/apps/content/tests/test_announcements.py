"""The announcements of the team: a picture or a video, a promo code, shown where and when the
team chooses; a refused file is said next to the field, never with an error page."""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.content.admin import safe_link
from apps.content.models import Banner
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory

pytestmark = pytest.mark.django_db
ADD = "admin:content_banner_add"


@pytest.fixture
def boss(client):
    user = get_user_model().objects.create_superuser(email="owner@example.com", password="s3c-ret1")
    client.force_login(user)
    return user


def picture(size=(800, 350)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 16, 46)).save(buffer, "JPEG")
    return buffer.getvalue()


def form_data(**changes):
    return {
        "title_fr": "Fête des mères",
        "text_fr": "Offre un moment à celle qui compte.",
        "cta_fr": "Offrir",
        "link": "/offrir",
        "promo_code": " maman10 ",
        "placements": ["home", "explore"],
        "position": "0",
        "is_active": "on",
        **changes,
    }


def test_an_announcement_with_a_picture_a_code_places_and_countries(client, boss):
    CountryFactory(code="BJ", name="Bénin", is_active=True)
    CountryFactory(code="FR", name="France", is_active=True)
    upload = SimpleUploadedFile("mothers.jpg", picture(), "image/jpeg")
    answer = client.post(reverse(ADD), form_data(upload=upload, countries=["FR"]))
    assert answer.status_code == 302, answer.context["adminform"].form.errors
    banner = Banner.objects.get()
    assert banner.promo_code == "MAMAN10" and banner.placements == ["home", "explore"]
    assert banner.countries == ["FR"] and banner.image.kind == "image"
    assert banner.state() == "live"

    listed = client.get(reverse("admin:content_banner_changelist"))
    assert listed.status_code == 200 and "Fête des mères" in listed.content.decode()

    api = APIClient()
    home = api.get("/api/v1/content/banners?country=FR").json()
    assert home[0]["promo_code"] == "MAMAN10" and home[0]["video"] is None
    assert api.get("/api/v1/content/banners?country=BJ").json() == []
    assert len(api.get("/api/v1/content/banners?placement=explore&country=FR").json()) == 1
    assert api.get("/api/v1/content/banners?placement=academy&country=FR").json() == []
    assert api.get("/api/v1/content/banners?placement=nowhere").status_code == 400


def test_a_file_too_large_is_said_next_to_the_field(client, boss):
    PlatformSettingFactory(key="media.image_max_bytes", value="1000")
    upload = SimpleUploadedFile("big.jpg", picture((1600, 900)), "image/jpeg")
    answer = client.post(reverse(ADD), form_data(upload=upload))
    assert answer.status_code == 200
    assert "upload" in answer.context["adminform"].form.errors
    assert not Banner.objects.exists()


def test_a_refusal_raised_while_saving_is_a_message_not_an_error_page(client, boss, monkeypatch):
    from apps.content import admin as content_admin
    from apps.core.media import errors as media_errors

    def refused(**kwargs):
        raise media_errors.FileTooLarge(media_errors.FileTooLarge.message % {"size": 15})

    monkeypatch.setattr(content_admin, "create_asset", refused)
    upload = SimpleUploadedFile("mothers.jpg", picture(), "image/jpeg")
    answer = client.post(reverse(ADD), form_data(upload=upload), follow=True)
    assert answer.status_code == 200
    assert "15" in " ".join(str(m) for m in answer.context["messages"])
    assert not Banner.objects.exists()


def test_form_rules(client, boss):
    wrong = client.post(reverse(ADD), form_data(link="javascript:alert(1)"))
    assert "link" in wrong.context["adminform"].form.errors
    no_link = client.post(reverse(ADD), form_data(link=""))
    assert "link" in no_link.context["adminform"].form.errors
    nowhere = client.post(reverse(ADD), form_data(placements=[]))
    assert "placements" in nowhere.context["adminform"].form.errors
    now = timezone.now()
    backwards = client.post(
        reverse(ADD),
        form_data(
            starts_at_0=now.date().isoformat(),
            starts_at_1="12:00",
            ends_at_0=now.date().isoformat(),
            ends_at_1="11:00",
        ),
    )
    assert "ends_at" in backwards.context["adminform"].form.errors
    assert safe_link("/explore") and safe_link("https://solangeglow.com") and safe_link("")
    assert not safe_link("//evil.example") and not safe_link("http://plain.example")


def test_states_and_switches(client, boss):
    now = timezone.now()
    live = Banner.objects.create(title="A")
    later = Banner.objects.create(title="B", starts_at=now + timezone.timedelta(days=1))
    over = Banner.objects.create(title="C", ends_at=now - timezone.timedelta(days=1))
    assert [b.state() for b in (live, later, over)] == ["live", "scheduled", "ended"]
    url = reverse("admin:content_banner_changelist")
    client.post(url, {"action": "switch_off", "_selected_action": [live.pk]})
    live.refresh_from_db()
    assert live.state() == "off"
    client.post(url, {"action": "switch_on", "_selected_action": [live.pk]})
    live.refresh_from_db()
    assert live.is_active
    page = client.get(reverse("admin:content_banner_change", args=[live.pk]))
    assert page.status_code == 200
    removed = client.post(
        reverse("admin:content_banner_change", args=[live.pk]),
        form_data(title_fr="A", remove_media="on"),
    )
    assert removed.status_code == 302
