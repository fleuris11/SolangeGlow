"""The ads through the API: a placement asked by a screen, the click link, the filler,
the page « Boost my showcase »; and the back office (lists, preview, export)."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ads.models import AdStat, Advertiser, Campaign, Creative
from apps.core.models import PlatformSetting
from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.tests.factories import adult
from apps.pros.tests.factories import ProFactory

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}
JSON = PlatformSetting.ValueType.JSON


def running(placement="home_banner", kind="sold"):
    found = Campaign.objects.create(
        advertiser=Advertiser.objects.create(name="Karité Doux"),
        name="Rentrée",
        kind=kind,
        status="active",
        starts_at=timezone.now() - datetime.timedelta(hours=1),
        ends_at=timezone.now() + datetime.timedelta(days=3),
    )
    Creative.objects.create(
        campaign=found,
        name="Visuel",
        format="image",
        placements=[placement],
        title="Le karité qui nourrit",
        cta="Voir",
        link="/selection",
    )
    return found


def test_a_screen_gets_its_ad_with_the_sponsor_and_a_click_link():
    running()
    client = APIClient()
    client.cookies["sg_visitor"] = "abc"
    found = client.get("/api/v1/ads?placement=home_banner&country=BJ").json()
    ad = found["results"][0]
    assert (ad["sponsor"], ad["title"], ad["house"]) == (
        "Karité Doux",
        "Le karité qui nourrit",
        False,
    )
    assert ad["click_url"].startswith("/api/v1/ads/click/")
    assert found["adsense"] is None
    moved = client.get(ad["click_url"])
    assert moved.status_code == 302
    assert moved["Location"] == "/selection"
    stat = AdStat.objects.get()
    assert (stat.impressions, stat.clicks) == (1, 1)


def test_a_broken_click_link_goes_home():
    assert APIClient().get("/api/v1/ads/click/nope")["Location"] == "/"


def test_adsense_fills_only_when_set_and_nothing_is_sold():
    client = APIClient()
    empty = client.get("/api/v1/ads?placement=search").json()
    assert (empty["results"], empty["adsense"], empty["feed_every"]) == ([], None, 6)
    PlatformSettingFactory(key="ads.filler", value='{"search": "adsense"}', value_type=JSON)
    PlatformSettingFactory(
        key="ads.adsense_client",
        value="ca-pub-123",
        value_type=PlatformSetting.ValueType.STRING,
    )
    PlatformSettingFactory(key="ads.adsense_slots", value='{"search": "999"}', value_type=JSON)
    assert client.get("/api/v1/ads?placement=search").json()["adsense"] == {
        "client": "ca-pub-123",
        "slot": "999",
    }


def test_boost_page_and_payment_page():
    pro = ProFactory(user=adult("Aïcha"), city="Cotonou", trades=["braids"])
    client = APIClient()
    client.force_authenticate(pro.user)
    page = client.get("/api/v1/ads/boosts").json()
    assert page["prices"] == {"currency": "XOF", "day": 1000, "week": 5000}
    assert page["running_until"] is None
    bought = client.post("/api/v1/ads/boosts", {"duration": "week"}, format="json", **H)
    assert bought.status_code == 200
    assert bought.json()["checkout_url"]
    assert client.get("/api/v1/ads/boosts").json()["boosts"][0]["status"] == "waiting_payment"
    client.force_authenticate(adult("Awa"))
    assert client.get("/api/v1/ads/boosts").status_code == 403


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser(
        email="owner@example.com", password="s3cret-pass"
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize("model", ["advertiser", "campaign", "creative", "boost", "adstat"])
def test_every_list_of_the_back_office_opens(admin_client, model):
    assert admin_client.get(reverse(f"admin:ads_{model}_changelist")).status_code == 200


def test_preview_and_export_of_a_campaign(admin_client):
    found = running()
    preview = admin_client.get(reverse("admin:ads_campaign_preview_detail", args=[found.pk]))
    assert preview.status_code == 200
    assert "Le karité qui nourrit" in preview.content.decode()
    APIClient().get("/api/v1/ads?placement=home_banner")
    export = admin_client.get(reverse("admin:ads_campaign_export_detail", args=[found.pk]))
    lines = export.content.decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 2
    assert lines[1].endswith(";1;0;0")
    assert admin_client.get(reverse("admin:ads_campaign_add")).status_code == 200
    assert admin_client.get(reverse("admin:ads_creative_add")).status_code == 200
