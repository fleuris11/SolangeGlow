"""Prospecting by e-mail: a showcase prepared for a professional (nothing public), a standard
e-mail with her personal link, her password, and « not interested » honoured for good."""

import re
from smtplib import SMTPDataError
from urllib.parse import unquote

import pytest
from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from apps.backoffice import errors, tasks
from apps.backoffice.models import Prospect, ProspectEmailTemplate, ProspectMessage
from apps.backoffice.services import prospects
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory
from apps.pros.models import ProProfile, Trade

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def boss(client):
    user = User.objects.create_superuser(email="owner@example.com", password="s3c-ret1")
    client.force_login(user)
    return user


@pytest.fixture
def lea():
    CountryFactory(code="FR", name="France", is_active=True)
    Trade.objects.get_or_create(key="braids", defaults={"name": "Tresses"})
    return Prospect.objects.create(
        name="Léa Martin",
        business_name="Atelier Léa",
        email="Lea@Example.com",
        city="Lyon",
        country="FR",
        trade="braids",
        services="Tresses, nattes collées, soins du cuir chevelu.",
        pitch="Vos tresses méritent d'être vues par tout Lyon.",
    )


def template(key):
    return ProspectEmailTemplate.objects.get(key=key)


def test_standard_e_mails_exist_in_three_languages():
    keys = set(ProspectEmailTemplate.objects.values_list("key", flat=True))
    assert keys >= {"presentation", "showcase_ready", "reminder"}
    ready = template("showcase_ready")
    assert ready.needs_showcase and "{{ link }}" in ready.body_fr
    for language in ("fr", "en", "sk"):
        assert "{{ stop_link }}" in getattr(ready, f"body_{language}")
    assert prospects.default_language("SK") == "sk"
    assert prospects.default_language("BJ") == "fr" and prospects.default_language("US") == "en"


def test_the_presentation_e_mail_is_written_for_her_and_followed(boss, lea, settings):
    settings.SITE_URL = "https://solangeglow.com"
    PlatformSettingFactory(
        key="prospects.reply_to", value="contact@solangeglow.com", value_type="string"
    )
    message = prospects.send_email(lea, template("presentation"), actor=boss)
    lea.refresh_from_db()
    assert lea.status == Prospect.Status.CONTACTED and lea.last_message_at and lea.invited_at
    [sent] = mail.outbox
    assert sent.to == ["lea@example.com"] and sent.reply_to == ["contact@solangeglow.com"]
    assert sent.subject.startswith("Atelier Léa")
    assert "Bonjour Léa," in sent.body and "Vos tresses méritent" in sent.body
    assert f"https://solangeglow.com/fr/pro/start?invite={lea.invite_code}" in sent.body
    assert f"/api/v1/prospects/{lea.invite_code}/stop" in sent.body
    message.refresh_from_db()
    assert message.status == ProspectMessage.Status.SENT and message.sent_by == boss
    assert str(message).startswith("lea@example.com")


def test_an_empty_proposal_leaves_no_hole(boss, lea):
    lea.pitch = ""
    lea.save()
    subject, body = prospects.compose(lea, template("presentation"))
    assert "\n\n\n" not in body and "{{" not in body and subject


def test_a_prepared_showcase_then_her_own_password(boss, lea, settings):
    settings.SITE_URL = "https://solangeglow.com"
    with pytest.raises(errors.ShowcaseNeeded):
        prospects.send_email(lea, template("showcase_ready"), actor=boss)

    pro = prospects.prepare_showcase(lea, actor=boss)
    assert prospects.prepare_showcase(lea, actor=boss) == pro  # once
    user = pro.user
    assert user.email == "lea@example.com" and not user.has_usable_password()
    assert pro.status == ProProfile.Status.DRAFT and pro.business_name == "Atelier Léa"
    assert pro.bio.startswith("Tresses") and list(pro.trades.values_list("key", flat=True)) == [
        "braids"
    ]
    # Nothing public: the draft is not in the search nor at its address.
    assert APIClient().get(f"/api/v1/pros/{pro.slug}").status_code == 404

    lea.refresh_from_db()
    prospects.send_email(lea, template("showcase_ready"), actor=boss)
    body = mail.outbox[-1].body
    token = unquote(re.search(r"/fr/auth/reset\?token=(\S+)", body).group(1))
    api = APIClient(HTTP_X_SG_CLIENT="web")
    done = api.post(
        reverse("v1:password-reset"),
        {"token": token, "password": "Tresses-Lyon-2026"},
        format="json",
    )
    assert done.status_code == 200 and done.json()["user"]["onboarding_required"] is True
    user.refresh_from_db()
    assert user.check_password("Tresses-Lyon-2026") and user.email_verified_at
    lea.refresh_from_db()
    assert lea.status == Prospect.Status.SIGNED_UP and lea.signed_up_user == user
    # The link worked once.
    again = api.post(
        reverse("v1:password-reset"),
        {"token": token, "password": "Autre-Mot-9-Passe"},
        format="json",
    )
    assert again.status_code == 400


def test_refusals_of_the_showcase(boss, lea):
    User.objects.create_user(email="lea@example.com", password="Rose-Hibiscus-2026")
    with pytest.raises(errors.ProspectAccountExists):
        prospects.prepare_showcase(lea, actor=boss)
    nobody = Prospect.objects.create(name="Sans Adresse")
    with pytest.raises(errors.ProspectEmailNeeded):
        prospects.prepare_showcase(nobody, actor=boss)
    with pytest.raises(errors.ProspectEmailNeeded):
        prospects.send_email(nobody, template("presentation"), actor=boss)


def test_not_interested_stops_the_e_mails_for_good(client, boss, lea):
    url = reverse("v1:prospects-stop", args=[lea.invite_code])
    asked = client.get(url)
    assert asked.status_code == 200 and "noindex" in asked["X-Robots-Tag"]
    lea.refresh_from_db()
    assert lea.status == Prospect.Status.NEW  # opening the link changes nothing
    assert client.post(url).status_code == 200
    lea.refresh_from_db()
    assert lea.status == Prospect.Status.DECLINED
    with pytest.raises(errors.ProspectDeclined):
        prospects.send_email(lea, template("presentation"), actor=boss)
    assert client.get(reverse("v1:prospects-stop", args=["unknown"])).status_code == 404
    assert prospects.decline("unknown") is False


def test_a_day_has_a_limit(boss, lea):
    PlatformSettingFactory(key="prospects.daily_email_limit", value="1")
    prospects.send_email(lea, template("presentation"), actor=boss)
    with pytest.raises(errors.DailyEmailLimit) as caught:
        prospects.send_email(lea, template("reminder"), actor=boss)
    assert "1" in caught.value.text()


def test_a_refused_e_mail_is_tried_again_then_marked(boss, lea, monkeypatch):
    message = ProspectMessage.objects.create(
        prospect=lea, to_email="lea@example.com", subject="Bonjour", body="Texte"
    )

    def refused(self, *args, **kwargs):
        raise SMTPDataError(502, b"not yet activated")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", refused)
    with pytest.raises(Retry):
        tasks.send_prospect_message.apply(args=(str(message.pk),))
    assert tasks.send_prospect_message.apply(args=(str(message.pk),), retries=4).result == "failed"
    message.refresh_from_db()
    assert message.status == ProspectMessage.Status.FAILED and message.error == "SMTPDataError"
    assert prospects.deliver("00000000-0000-0000-0000-000000000000") == "skipped"


def test_the_whole_thing_from_the_admin(client, boss, lea):
    change = reverse("admin:backoffice_prospect_change", args=[lea.pk])
    assert client.get(change).status_code == 200
    email_page = reverse("admin:backoffice_prospect_email", args=[lea.pk])

    # Before the showcase: the presentation is proposed, the « ready » e-mail says what misses.
    page = client.get(email_page)
    assert page.status_code == 200 and page.context["chosen"].key == "presentation"
    assert "Bonjour Léa," in page.context["preview"][1]
    blocked = client.get(email_page + "?template=showcase_ready")
    assert blocked.context["problem"] and blocked.context["preview"] is None

    prepared = client.get(
        reverse("admin:backoffice_prospect_prepare_showcase_detail", args=[lea.pk])
    )
    assert prepared.status_code == 302
    lea.refresh_from_db()
    assert lea.pro_id
    opened = client.get(reverse("admin:backoffice_prospect_open_showcase_detail", args=[lea.pk]))
    assert opened.status_code == 302 and str(lea.pro.user_id) in opened["Location"]

    sent = client.post(email_page, {"template": "showcase_ready"})
    assert sent.status_code == 302 and len(mail.outbox) == 1
    listed = client.get(reverse("admin:backoffice_prospect_changelist"))
    assert listed.status_code == 200 and "Atelier Léa" in listed.content.decode()

    # In bulk, and the journal.
    other = Prospect.objects.create(name="Sans Adresse")
    bulk = client.post(
        reverse("admin:backoffice_prospect_changelist"),
        {"action": "email_presentation", "_selected_action": [lea.pk, other.pk]},
        follow=True,
    )
    assert bulk.status_code == 200 and len(mail.outbox) == 2
    assert client.get(reverse("admin:backoffice_prospectmessage_changelist")).status_code == 200
    templates = client.get(reverse("admin:backoffice_prospectemailtemplate_changelist"))
    assert templates.status_code == 200

    # A refusal raised by an action is a message, never an error page.
    twin = Prospect.objects.create(name="Jumelle", email="lea@example.com")
    refused = client.get(
        reverse("admin:backoffice_prospect_prepare_showcase_detail", args=[twin.pk]), follow=True
    )
    assert refused.status_code == 200
    assert any("already" in str(m) or "déjà" in str(m) for m in refused.context["messages"])
