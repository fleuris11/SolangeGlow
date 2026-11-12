"""A showcase prepared by the team to put a professional's work forward: online with the band
« prepared by Solange Glow », their WhatsApp, no online booking, removable in one click; a
WhatsApp message and an e-mail written for them; the page is theirs once they chose a password."""

import re
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from apps.backoffice import errors
from apps.backoffice.models import Prospect, ProspectEmailTemplate
from apps.backoffice.services import prospects
from apps.booking.models import BookingSettings
from apps.core.tests.factories import CountryFactory
from apps.pros.models import ProProfile, Trade
from apps.pros.tests.factories import COTONOU, add_service

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def boss(client):
    user = User.objects.create_superuser(email="owner@example.com", password="s3c-ret1")
    client.force_login(user)
    return user


@pytest.fixture
def kofi(settings):
    settings.SITE_URL = "https://solangeglow.com"
    CountryFactory(code="BJ", name="Bénin", is_active=True)
    Trade.objects.get_or_create(key="barber", defaults={"name": "Barbier"})
    return Prospect.objects.create(
        name="Kofi Adjovi",
        business_name="Kofi Cuts",
        email="kofi@example.com",
        phone="01 97 12 34 56",
        address="Rue 12, Akpakpa",
        city="Cotonou",
        country="BJ",
        language="fr",
        trade="barber",
        website="instagram.com/kofi.cuts",
        services="Dégradés, tailles de barbe, soins.",
        pitch="Vos dégradés méritent d'être vus par tout Cotonou.",
    )


def complete(pro):
    """What the team adds as them: their place on the map and a service."""
    pro.location = COTONOU
    pro.save(update_fields=["location"])
    add_service(pro, name="Dégradé", price=3000, minutes=45)


def test_prepared_with_what_we_know_and_booking_paused(boss, kofi):
    pro = prospects.prepare_showcase(kofi, actor=boss)
    assert pro.prepared_by_team and pro.address == "Rue 12, Akpakpa" and pro.receives_clients
    assert pro.social_links["whatsapp"] == "+2290197123456"
    assert pro.social_links["instagram"] == "https://instagram.com/kofi.cuts"
    assert BookingSettings.objects.get(pro=pro).online_paused
    assert prospects.activity(kofi) == "Barbier, Cotonou"


def test_publish_says_what_is_missing_then_puts_it_online(client, boss, kofi):
    publish = reverse("admin:backoffice_prospect_publish_showcase_detail", args=[kofi.pk])
    before = client.get(publish, follow=True)
    assert any("Prepare" in str(m) or "Prépare" in str(m) for m in before.context["messages"])

    pro = prospects.prepare_showcase(kofi, actor=boss)
    kofi.refresh_from_db()
    missing = client.get(publish, follow=True)
    text = " ".join(str(m) for m in missing.context["messages"])
    assert "map" in text or "carte" in text
    with pytest.raises(errors.ShowcaseNotOnline):
        prospects.compose(kofi, ProspectEmailTemplate.objects.get(key="showcase_ready"))

    complete(pro)
    assert client.get(publish).status_code == 302
    pro.refresh_from_db()
    assert pro.status == ProProfile.Status.PUBLISHED
    kofi.refresh_from_db()
    assert prospects.showcase_link(kofi) == f"https://solangeglow.com/fr/{pro.slug}"

    page = APIClient().get(f"/api/v1/pros/{pro.slug}").json()
    assert page["prepared"] == {"whatsapp": "2290197123456"}
    change = client.get(reverse("admin:backoffice_prospect_change", args=[kofi.pk]))
    assert prospects.showcase_link(kofi) in change.content.decode()


def test_whatsapp_written_for_them_and_shared(client, boss, kofi):
    share = reverse("admin:backoffice_prospect_share_detail", args=[kofi.pk])
    assert client.get(share).status_code == 302  # back to the file: nothing online yet
    pro = prospects.prepare_showcase(kofi, actor=boss)
    complete(pro)
    prospects.publish_showcase(kofi, actor=boss)

    opened = client.get(reverse("admin:backoffice_prospect_whatsapp_detail", args=[kofi.pk]))
    url = urlparse(opened["Location"])
    assert url.netloc == "wa.me" and url.path == "/2290197123456"
    text = parse_qs(url.query)["text"][0]
    assert text.startswith("Bonjour Kofi") and "Kofi Cuts (Barbier, Cotonou)" in text
    assert f"/fr/{pro.slug}" in text and "/fr/auth/reset?token=" in text
    kofi.refresh_from_db()
    assert kofi.status == Prospect.Status.CONTACTED and kofi.invited_at

    shared = urlparse(client.get(share)["Location"])
    assert shared.netloc == "wa.me" and f"/fr/{pro.slug}" in parse_qs(shared.query)["text"][0]

    nobody = Prospect.objects.create(name="Sans Numéro")
    blocked = client.get(
        reverse("admin:backoffice_prospect_whatsapp_detail", args=[nobody.pk]), follow=True
    )
    assert blocked.status_code == 200 and blocked.redirect_chain[-1][0].endswith("/change/")


def test_the_e_mail_then_their_password_makes_the_page_theirs(boss, kofi):
    pro = prospects.prepare_showcase(kofi, actor=boss)
    complete(pro)
    prospects.publish_showcase(kofi, actor=boss)
    assert mail.outbox == []  # no automatic « published » e-mail: the team writes itself
    prospects.send_email(kofi, ProspectEmailTemplate.objects.get(key="showcase_ready"), actor=boss)
    [sent] = mail.outbox
    body = sent.body
    assert "Kofi Cuts (Barbier, Cotonou)" in body and f"/fr/{pro.slug}" in body
    token = unquote(re.search(r"/fr/auth/reset\?token=(\S+)", body).group(1))
    api = APIClient(HTTP_X_SG_CLIENT="web")
    done = api.post(
        reverse("v1:password-reset"), {"token": token, "password": "Degrade-Cotonou-26"}
    )
    assert done.status_code == 200
    pro.refresh_from_db()
    assert not pro.prepared_by_team
    assert APIClient().get(f"/api/v1/pros/{pro.slug}").json()["prepared"] is None


def test_remove_my_page_in_one_click(boss, kofi):
    pro = prospects.prepare_showcase(kofi, actor=boss)
    complete(pro)
    prospects.publish_showcase(kofi, actor=boss)
    api = APIClient(HTTP_X_SG_CLIENT="web")
    answer = api.post(f"/api/v1/pros/{pro.slug}/removal")
    assert answer.status_code == 200 and answer.json() == {"removed": True}
    pro.refresh_from_db()
    kofi.refresh_from_db()
    assert pro.status == ProProfile.Status.DRAFT and kofi.status == Prospect.Status.DECLINED
    assert api.post(f"/api/v1/pros/{pro.slug}/removal").status_code == 404
    with pytest.raises(errors.ProspectDeclined):
        prospects.publish_showcase(kofi, actor=boss)


def test_not_interested_also_takes_the_page_offline(client, boss, kofi):
    pro = prospects.prepare_showcase(kofi, actor=boss)
    complete(pro)
    prospects.publish_showcase(kofi, actor=boss)
    client.post(reverse("v1:prospects-stop", args=[kofi.invite_code]))
    pro.refresh_from_db()
    assert pro.status == ProProfile.Status.DRAFT


def test_a_page_of_their_own_cannot_be_removed_by_others(kofi):
    from apps.pros.tests.factories import ProFactory

    own = ProFactory(status=ProProfile.Status.PUBLISHED)
    answer = APIClient(HTTP_X_SG_CLIENT="web").post(f"/api/v1/pros/{own.slug}/removal")
    assert answer.status_code == 404


def test_links_and_numbers(kofi):
    kofi.website = "@kofi.cuts"
    assert prospects.social_links(kofi)["instagram"] == "@kofi.cuts"
    kofi.website = "kofi-cuts.com"
    assert prospects.social_links(kofi)["website"] == "https://kofi-cuts.com"
    kofi.phone = "+33 6 12 34 56 78"
    assert prospects.whatsapp_number(kofi) == "33612345678"
    kofi.phone = "12"
    assert prospects.whatsapp_number(kofi) == ""
    kofi.phone = "abc"
    assert prospects.whatsapp_number(kofi) == ""
