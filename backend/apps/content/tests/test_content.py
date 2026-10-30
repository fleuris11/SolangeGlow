"""Contents and help center: pages and banners translated and versioned, FAQ, suggestions
before a ticket, tickets answered from the admin."""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from apps.content.models import ContentVersion, FaqItem, Page, Ticket
from apps.content.services import help as help_services
from apps.content.services import versions
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


@pytest.fixture
def boss(client):
    user = get_user_model().objects.create_superuser(email="owner@example.com", password="s3c-ret1")
    client.force_login(user)
    return user


def test_legal_pages_are_served_in_the_language_of_the_app():
    pages = APIClient().get("/api/v1/content/pages").json()
    assert {p["kind"] for p in pages} >= {"terms", "privacy", "legal", "game_rules", "returns"}
    english = (
        APIClient().get("/api/v1/content/pages/regles-des-jeux", HTTP_ACCEPT_LANGUAGE="en").json()
    )
    assert english["title"] == "Rules of the games"
    assert APIClient().get("/api/v1/content/pages/nope").status_code == 404


def test_every_save_is_a_version_that_can_come_back(client, boss):
    page = Page.objects.get(slug="mentions-legales")
    url = reverse("admin:content_page_change", args=[page.pk])
    form = client.get(url).context["adminform"].form
    data = {key: value for key, value in form.initial.items() if value is not None}
    data.update({"title_fr": "Mentions légales v2", "slug": page.slug, "kind": page.kind})
    for name in ("title_en", "title_sk", "body_fr", "body_en", "body_sk", "summary_fr"):
        data.setdefault(name, getattr(page, name) or "")
    data.setdefault("position", page.position)
    data["is_published"] = "on"
    assert client.post(url, data).status_code == 302
    page.refresh_from_db()
    assert (page.title_fr, page.version) == ("Mentions légales v2", 1)
    first = ContentVersion.objects.get(object_id=str(page.pk))
    page.title_fr = "Changement à la main"
    page.save()
    versions.snapshot(page)
    history = client.get(reverse("admin:content_page_versions_detail", args=[page.pk]))
    assert "Changement à la main" in history.content.decode()
    client.post(
        reverse("admin:content_page_versions_detail", args=[page.pk]), {"version": first.pk}
    )
    page.refresh_from_db()
    assert page.title_fr == "Mentions légales v2"
    assert page.version == 3


def test_home_banners_by_date_and_country():
    from apps.content.models import Banner

    Banner.objects.create(title="Fête des mères", countries=["FR"])
    Banner.objects.create(title="Rentrée au Bénin", countries=["BJ"], position=1)
    found = APIClient().get("/api/v1/content/banners?country=BJ").json()
    assert [b["title"] for b in found] == ["Rentrée au Bénin"]


def test_faq_by_topic_and_suggestions_before_a_ticket():
    topics = APIClient().get("/api/v1/help/faq").json()
    assert topics and topics[0]["items"]
    found = (
        APIClient()
        .post(
            "/api/v1/help/suggest",
            {"question": "Je veux annuler mon rendez-vous"},
            format="json",
            **H,
        )
        .json()
    )
    assert found["answer"] is None  # no AI yet
    assert "annuler" in found["faq"][0]["question"].lower()


def test_a_ticket_without_account_is_answered_by_email(client, boss):
    created = APIClient().post(
        "/api/v1/help/tickets",
        {"name": "Inès", "email": "ines@example.com", "message": "Mon colis n'est pas arrivé."},
        format="json",
        **H,
    )
    assert created.status_code == 201
    ticket = Ticket.objects.get(reference=created.json()["reference"])
    url = reverse("admin:content_ticket_answer_detail", args=[ticket.pk])
    assert client.get(url).status_code == 200
    client.post(url, {"answer": "Il arrive jeudi au point de retrait."})
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.ANSWERED
    assert mail.outbox and "jeudi" in mail.outbox[-1].body


def test_a_ticket_of_a_member_is_answered_in_the_app(boss):
    awa = adult()
    app = APIClient()
    app.force_authenticate(awa)
    reference = app.post(
        "/api/v1/help/tickets", {"message": "Comment changer mon numéro ?"}, format="json", **H
    ).json()["reference"]
    help_services.answer(Ticket.objects.get(reference=reference), "Dans « Moi ».", actor=boss)
    assert Notification.objects.filter(user=awa, event_key="help.ticket_answered").exists()


def test_a_ticket_needs_a_way_to_answer():
    refused = APIClient().post("/api/v1/help/tickets", {"message": "Bonjour"}, format="json", **H)
    assert refused.status_code == 400
    assert refused.json()["code"] == "help_contact_needed"


def test_faq_versions_too(boss):
    item = FaqItem.objects.first()
    versions.snapshot(item, author=boss)
    assert versions.history(item).count() == 1
