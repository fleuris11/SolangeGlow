import datetime

import httpx
import pytest
import respx
from django.utils import timezone

from apps.core.tests.factories import PlatformSettingFactory
from apps.moderation import errors, providers, services
from apps.moderation.models import ModerationCase, Sanction
from apps.moderation.selectors import active_sanction, can_post
from apps.notifications.models import Notification
from apps.social.models import Visibility
from apps.social.tests.factories import person, published_post

pytestmark = pytest.mark.django_db
AI_URL = "https://moderation.example/v1/check"


def words(key, values):
    import json

    PlatformSettingFactory(key=key, value_type="json", value=json.dumps(values))


# --- Rules -------------------------------------------------------------------------------


def test_rules_block_forbidden_words_even_with_accents_and_capitals():
    words("moderation.blocked_words", ["encule"])
    verdict = providers.RulesModerationProvider().check_text("Espèce d'ENCULÉ")
    assert (verdict.action, verdict.labels) == ("block", ["blocked_word"])
    assert providers.RulesModerationProvider().check_text("Bonjour").action == "allow"


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("C'est une arnaque totale", "sensitive_word"),
        ("Paie par Western Union stp", "payment_outside"),
        ("Écris-moi au +33 6 12 34 01 07", "contact_outside"),
        ("ACHETEZ MAINTENANT LES MEILLEURS PRODUITS", "shouting"),
    ],
)
def test_rules_put_doubtful_texts_in_the_queue(text, label):
    words("moderation.review_words", ["arnaque"])
    verdict = providers.RulesModerationProvider().check_text(text)
    assert verdict.action == "review" and label in verdict.labels


def test_phone_numbers_can_be_allowed_by_a_setting():
    PlatformSettingFactory(key="moderation.flag_phone_numbers", value_type="boolean", value="false")
    assert providers.RulesModerationProvider().check_text("Appelle le 0197123456").action == "allow"


# --- AI provider -------------------------------------------------------------------------


def test_ai_is_skipped_without_keys():
    with pytest.raises(providers.ProviderNotConfigured):
        providers.AiModerationProvider().check_text("hello")
    assert providers.check(text="hello").action == "allow"


@respx.mock
def test_ai_flags_and_severe_categories_block(settings):
    settings.MODERATION_AI_URL, settings.MODERATION_AI_KEY = AI_URL, "secret"
    respx.post(AI_URL).mock(
        side_effect=[
            httpx.Response(200, json={"flagged": True, "categories": {"harassment": True}}),
            httpx.Response(200, json={"flagged": True, "categories": {"sexual/minors": True}}),
            httpx.Response(200, json={"flagged": False, "categories": {}}),
        ]
    )
    assert providers.check(text="a").action == "review"
    blocked = providers.check(text="b")
    assert (blocked.action, blocked.labels, blocked.provider) == ("block", ["sexual/minors"], "ai")
    assert providers.check(text="c").action == "allow"


@respx.mock
def test_ai_down_keeps_the_content_but_queues_it(settings):
    settings.MODERATION_AI_URL, settings.MODERATION_AI_KEY = AI_URL, "secret"
    respx.post(AI_URL).mock(return_value=httpx.Response(503))
    verdict = providers.check(text="bonjour")
    assert verdict.action == "review" and verdict.labels == ["check_failed"]


# --- Reports, blocks, hides --------------------------------------------------------------


def test_reports_open_one_case_and_hide_at_the_threshold():
    PlatformSettingFactory(key="moderation.auto_hide_reports", value="2")
    author = person()
    post = published_post(author)
    first, second = person(name="A"), person(name="B")
    services.report(first, post, reason="spam")
    post.refresh_from_db()
    assert post.visibility == Visibility.VISIBLE
    with pytest.raises(errors.AlreadyReported):
        services.report(first, post, reason="spam")
    services.report(second, post, reason="scam", comment="Demande de payer hors appli")
    post.refresh_from_db()
    case = ModerationCase.objects.get()
    assert post.visibility == Visibility.HELD
    assert (case.report_count, case.hidden_until_review, case.author) == (2, True, author)
    with pytest.raises(errors.CannotReportYourself):
        services.report(author, post, reason="spam")


def test_a_person_can_be_reported():
    target = person(name="Faux compte")
    services.report(person(), target, reason="scam")
    assert ModerationCase.objects.get().author == target


# --- Decisions and sanctions ---------------------------------------------------------------


def decide_remove(post, actor, *, sanction=True):
    services.report(person(name=f"R{post.pk.hex[:4]}"), post, reason="harassment")
    case = ModerationCase.objects.get(target_id=post.pk, status="pending")
    return services.decide(case, actor=actor, keep=False, sanction=sanction, note="Insultes")


def test_keep_puts_the_content_back():
    PlatformSettingFactory(key="moderation.auto_hide_reports", value="1")
    post = published_post(person())
    services.report(person(name="R"), post, reason="spam")
    post.refresh_from_db()
    assert post.visibility == Visibility.HELD
    case = ModerationCase.objects.get()
    services.decide(case, actor=person(name="Team", is_staff=True), keep=True)
    post.refresh_from_db()
    assert post.visibility == Visibility.VISIBLE and case.status == "kept"


def test_sanctions_follow_the_ladder_up_to_the_ban():
    team = person(name="Team", is_staff=True)
    author = person(name="Troll")
    levels = []
    for _ in range(4):
        decide_remove(published_post(author), team)
        levels.append(Sanction.objects.filter(user=author).order_by("-created_at").first().level)
        author.refresh_from_db()
    assert levels == ["warning", "mute", "suspension", "ban"]
    assert not author.is_active
    assert active_sanction(author).level == "ban"
    assert Notification.objects.filter(user=author, event_key="moderation.sanction").count() >= 2
    assert Notification.objects.filter(user=author, event_key="moderation.content_removed").exists()


def test_mute_blocks_posting_only_for_a_while():
    author = person()
    sanction = services.apply_sanction(author, actor=None, level="mute")
    assert not can_post(author)
    Sanction.objects.filter(pk=sanction.pk).update(until=timezone.now() - datetime.timedelta(1))
    assert can_post(author)


def test_an_ended_suspension_gives_the_account_back():
    author = person()
    services.apply_sanction(author, actor=None, level="suspension")
    author.refresh_from_db()
    assert not author.is_active
    Sanction.objects.update(until=timezone.now() - datetime.timedelta(minutes=1))
    assert services.lift_expired_sanctions() == 1
    author.refresh_from_db()
    assert author.is_active


def test_a_ban_is_never_lifted():
    author = person()
    services.apply_sanction(author, actor=None, level="ban")
    assert services.lift_expired_sanctions() == 0


def test_the_ladder_is_a_setting():
    words("moderation.sanction_ladder", [{"level": "suspension", "days": 1}])
    author = person()
    decide_remove(published_post(author), person(name="Team", is_staff=True))
    assert Sanction.objects.get(user=author).level == "suspension"
