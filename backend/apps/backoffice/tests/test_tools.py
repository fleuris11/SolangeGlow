"""Tools of the back office: dashboard, translations corrected without redeploying, CSV
exports, the switches by country and role, prospecting."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import translation
from rest_framework.test import APIClient

from apps.backoffice.models import Prospect, TranslationOverride
from apps.backoffice.services import prospects, team, translations
from apps.core.audit.models import AuditEvent
from apps.core.models import FeatureFlag
from apps.core.selectors import is_feature_enabled
from apps.core.tests.factories import CountryFactory
from apps.messaging.tests.factories import adult
from apps.notifications.models import ContactMessage
from apps.pros.tests.factories import ProFactory

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def boss(client):
    user = User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")
    client.force_login(user)
    return user


def test_the_dashboard_shows_the_figures(client, boss):
    adult()
    page = client.get(reverse("admin:index") + "?period=7&country=BJ")
    html = page.content.decode()
    assert page.status_code == 200
    assert "canvas" in html  # the charts
    assert page.context["kpis"][0]["value"] >= 1


def test_the_dashboard_is_hidden_without_the_right(client):
    team.create_groups()
    moderator = team.save_member(
        email="mod@example.com",
        first_name="Mod",
        password="x-pass-1",
        roles=["moderation"],
        actor=None,
    )
    client.force_login(moderator)
    page = client.get(reverse("admin:index"))
    assert page.status_code == 200 and page.context["show_dashboard"] is False


def test_a_server_text_corrected_is_used_at_once(client, boss):
    original = "This page does not exist."
    translations.save(
        domain="server", language="fr", key=original, text="Page introuvable, désolé.", actor=boss
    )
    translations.apply_server()
    with translation.override("fr"):
        assert translation.gettext(original) == "Page introuvable, désolé."
    translations.save(domain="server", language="fr", key=original, text="", actor=boss)
    translations.apply_server()
    with translation.override("fr"):
        assert translation.gettext(original) != "Page introuvable, désolé."
    assert AuditEvent.objects.filter(action="backoffice.translation_changed").count() == 2


def test_web_corrections_are_served_to_the_app(boss):
    translations.save(
        domain="web", language="fr", key="home.question", text="Quoi de neuf ?", actor=boss
    )
    found = APIClient().get("/api/v1/i18n/overrides?lang=fr").json()
    assert found["messages"] == {"home.question": "Quoi de neuf ?"}
    assert APIClient().get("/api/v1/i18n/overrides?lang=en").json()["messages"] == {}


def test_search_and_save_from_the_translations_page(client, boss, monkeypatch):
    monkeypatch.setattr(
        translations, "web_catalog", lambda lang: {"home.question": "Tu cherches quoi ?"}
    )
    page = client.get(reverse("admin:backoffice_translations") + "?q=cherches&lang=fr")
    assert "home.question" in page.content.decode()
    client.post(
        reverse("admin:backoffice_translations"),
        {"domain": "web", "key": "home.question", "lang": "fr", "text": "Envie de quoi ?"},
    )
    assert TranslationOverride.objects.get().text == "Envie de quoi ?"


def test_every_list_exports_as_csv(client, boss):
    awa = adult()
    response = client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "export_csv", "index": "0", "_selected_action": [awa.pk, boss.pk]},
    )
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    lines = response.content.decode("utf-8-sig").strip().splitlines()
    assert len(lines) >= 2
    assert AuditEvent.objects.filter(action="backoffice.exported").exists()


def test_the_audit_journal_exports_too(client, boss):
    event = AuditEvent.objects.create(action="test.event")
    response = client.post(
        reverse("admin:core_auditevent_changelist"),
        {"action": "export_csv", "index": "0", "_selected_action": [event.pk]},
    )
    assert response["Content-Type"].startswith("text/csv")
    assert "test.event" in response.content.decode("utf-8-sig")


def test_switches_by_country_and_role(client, boss):
    benin = CountryFactory()
    flag = FeatureFlag.objects.get(key="gifts")
    url = reverse("admin:backoffice_flags")
    assert client.get(url).status_code == 200
    client.post(url, {"flag": flag.pk, "what": "enabled"})
    assert is_feature_enabled("gifts") is (not flag.is_enabled)
    client.post(url, {"flag": flag.pk, "what": "enabled"})
    client.post(url, {"flag": flag.pk, "what": f"country:{benin.code}"})
    assert is_feature_enabled("gifts", country="BJ") is True
    assert is_feature_enabled("gifts", country="FR") is False
    client.post(url, {"flag": flag.pk, "what": "role:pro"})
    assert is_feature_enabled("gifts", country="BJ", roles=["client"]) is False
    assert AuditEvent.objects.filter(action="backoffice.flag_changed").count() == 4


def test_prospects_import_invite_signup_and_active(client, boss):
    data = (
        "nom;activité;téléphone;ville;métier\n"
        "Rose;Rose Coiffure;+2290197001111;Cotonou;hair\n"
        "Rose bis;;+2290197001111;Cotonou;hair\n"
        ";;;;\n"
    ).encode()
    assert prospects.import_csv(data, actor=boss) == {"added": 1, "skipped": 2}
    prospect = Prospect.objects.get()
    assert prospects.invite(prospect, actor=boss) is True
    prospect.refresh_from_db()
    assert prospect.status == Prospect.Status.CONTACTED
    message = ContactMessage.objects.get(event_key="prospects.invitation")
    assert prospect.invite_code in message.body
    rose = adult("Rose")
    app = APIClient()
    app.force_authenticate(rose)
    assert (
        app.post(
            "/api/v1/prospects/claim",
            {"code": prospect.invite_code},
            format="json",
            HTTP_X_SG_CLIENT="web",
        ).status_code
        == 204
    )
    prospect.refresh_from_db()
    assert prospect.status == Prospect.Status.SIGNED_UP and prospect.signed_up_user == rose
    ProFactory(user=rose)
    assert prospects.promote_active() == 1
    prospect.refresh_from_db()
    assert prospect.status == Prospect.Status.ACTIVE


def test_prospect_import_page(client, boss):
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile("pros.csv", b"name,phone\nFifa,+2290197002222\n", "text/csv")
    response = client.post(reverse("admin:backoffice_prospects_import"), {"file": upload})
    assert response.status_code == 302
    assert Prospect.objects.filter(name="Fifa").exists()


@pytest.mark.parametrize(
    "name",
    [
        "admin:backoffice_prospect_changelist",
        "admin:backoffice_translationoverride_changelist",
        "admin:backoffice_impersonation_changelist",
        "admin:content_page_changelist",
        "admin:content_banner_changelist",
        "admin:content_faqitem_changelist",
        "admin:content_ticket_changelist",
        "admin:payments_dispute_changelist",
    ],
)
def test_lists_open(client, boss, name):
    assert client.get(reverse(name)).status_code == 200
