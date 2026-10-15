"""Sending: kinds of messages, resending, cards, fraud warning, away message, alerts."""

import datetime
import uuid

import pytest
from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging import errors, fraud, realtime, selectors, services
from apps.messaging.models import ConversationMember, Message
from apps.moderation.models import ModerationCase
from apps.notifications.models import Notification
from apps.pros.tests.factories import add_service, open_every_day
from apps.social.tests.factories import published_post

from .factories import adult, closed_today, pro, upload

pytestmark = pytest.mark.django_db


@pytest.fixture
def pair():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    return awa, aicha, services.start_direct(awa, aicha)


def test_text_photo_and_voice_messages(pair):
    awa, aicha, conversation = pair
    services.send(awa, conversation.pk, text="Bonjour, vous êtes libre samedi ?")
    photo = services.send(awa, conversation.pk, media_id=upload(awa).pk, text="Ce modèle")
    voice = services.send(aicha, conversation.pk, media_id=upload(aicha, "voice_note", "audio").pk)
    assert photo.kind == Message.Kind.PHOTO and photo.text == "Ce modèle"
    assert voice.kind == Message.Kind.VOICE
    conversation.refresh_from_db()
    assert conversation.last_message_at == voice.created_at


def test_files_must_be_hers_ready_and_meant_for_messages(pair):
    awa, aicha, conversation = pair
    with pytest.raises(errors.InvalidMedia):
        services.send(awa, conversation.pk, media_id=upload(aicha).pk)
    with pytest.raises(errors.InvalidMedia):
        services.send(awa, conversation.pk, media_id=upload(awa, purpose="post").pk)
    pending = upload(awa, status=MediaAsset.Status.PROCESSING)
    with pytest.raises(errors.MediaNotReady):
        services.send(awa, conversation.pk, media_id=pending.pk)


def test_empty_and_too_long_messages_are_refused(pair):
    awa, _, conversation = pair
    with pytest.raises(errors.EmptyMessage):
        services.send(awa, conversation.pk, text="   ")
    PlatformSettingFactory(key="messaging.max_text_length", value="10")
    with pytest.raises(errors.MessageTooLong):
        services.send(awa, conversation.pk, text="x" * 11)


def test_sending_twice_from_the_offline_queue_makes_one_message(pair):
    awa, _, conversation = pair
    client_id = uuid.uuid4()
    first = services.send(awa, conversation.pk, text="Bonjour", client_id=client_id)
    again = services.send(awa, conversation.pk, text="Bonjour", client_id=client_id)
    assert first.pk == again.pk
    assert conversation.messages.count() == 1


def test_sharing_a_post_a_service_and_a_free_slot(pair):
    awa, aicha, conversation = pair
    post = published_post(aicha, caption="Knotless mi-dos")
    card = services.send(awa, conversation.pk, share={"kind": "post", "id": str(post.pk)})
    assert card.kind == Message.Kind.SHARE
    assert card.share_data["link"] == f"/p/{post.pk}" and "Knotless" in card.share_data["text"]

    service = add_service(aicha.pro_profile, name="Nattes collées", price=5000)
    card = services.send(aicha, conversation.pk, share={"kind": "service", "id": str(service.pk)})
    assert card.share_data["title"] == "Nattes collées" and card.share_data["amount_minor"] == 5000

    when = (timezone.now() + datetime.timedelta(hours=3)).isoformat()
    slot = {"kind": "slot", "pro": aicha.pro_profile.slug, "starts_at": when}
    card = services.send(aicha, conversation.pk, share=slot)
    assert card.share_data["starts_at"] == when


def test_unknown_products_and_kinds_cannot_be_shared(pair):
    awa, _, conversation = pair
    with pytest.raises(errors.ShareNotFound):
        services.send(awa, conversation.pk, share={"kind": "product", "id": str(uuid.uuid4())})
    with pytest.raises(errors.ShareNotFound):
        services.send(awa, conversation.pk, share={"kind": "product", "id": "nope"})
    with pytest.raises(errors.ShareUnavailable):
        services.send(awa, conversation.pk, share={"kind": "course", "id": str(uuid.uuid4())})


def test_hidden_or_unknown_items_cannot_be_shared(pair):
    awa, _, conversation = pair
    with pytest.raises(errors.ShareNotFound):
        services.send(awa, conversation.pk, share={"kind": "post", "id": str(uuid.uuid4())})
    past = (timezone.now() - datetime.timedelta(days=2)).isoformat()
    with pytest.raises(errors.ShareNotFound):
        services.send(awa, conversation.pk, share={"kind": "slot", "pro": "x", "starts_at": past})


@pytest.mark.parametrize(
    ("text", "labels"),
    [
        ("Appelle-moi au 97 12 34 56", ["phone"]),
        ("Paie ici : https://revolut.me/aicha", ["payment_link"]),
        ("Envoie par Mobile Money stp", ["keyword"]),
        ("Je préfère un virement, c'est plus simple", ["keyword"]),
        ("Merci, à samedi !", []),
    ],
)
def test_fraud_signs(text, labels):
    assert fraud.check(text) == labels


def test_a_risky_message_shows_the_pay_in_the_app_warning(pair):
    _, aicha, conversation = pair
    message = services.send(aicha, conversation.pk, text="Envoie l'acompte par Western Union")
    conversation.refresh_from_db()
    assert message.fraud_labels == ["keyword"] and conversation.payment_warning


def test_no_warning_once_they_dealt_through_the_app(pair):
    _, aicha, conversation = pair

    def they_dealt(user, other):
        return True

    fraud.register_trust_check(they_dealt)
    try:
        message = services.send(aicha, conversation.pk, text="Mon numéro : 97 12 34 56")
    finally:
        fraud.unregister_trust_check(they_dealt)
    assert message.fraud_labels == []


def test_away_message_outside_opening_hours_once(pair):
    awa, aicha, conversation = pair
    closed_today(aicha)
    services.set_away_message(aicha, enabled=True, text="Je suis au salon demain dès 9 h.")
    services.send(awa, conversation.pk, text="Bonjour")
    services.send(awa, conversation.pk, text="Vous êtes là ?")
    automatic = conversation.messages.filter(is_automatic=True)
    assert automatic.count() == 1
    assert automatic.get().sender == aicha and automatic.get().text.startswith("Je suis au salon")


def test_no_away_message_while_open(pair):
    awa, aicha, conversation = pair
    open_every_day(aicha.pro_profile)
    services.set_away_message(aicha, enabled=True, text="Absente")
    services.send(awa, conversation.pk, text="Bonjour")
    assert not conversation.messages.filter(is_automatic=True).exists()


def test_quick_replies_and_away_message_are_for_pros():
    with pytest.raises(errors.NotAPro):
        services.save_quick_replies(adult("Awa"), ["Oui"])
    aicha = pro("Aïcha Tresses")
    saved = services.save_quick_replies(aicha, ["Oui c'est disponible", " ", "Voici mes tarifs"])
    assert [r.text for r in saved] == ["Oui c'est disponible", "Voici mes tarifs"]
    PlatformSettingFactory(key="messaging.quick_replies_max", value="1")
    with pytest.raises(errors.TooManyQuickReplies):
        services.save_quick_replies(aicha, ["Un", "Deux"])


def test_receipts_and_unread_counts(pair):
    awa, aicha, conversation = pair
    services.send(awa, conversation.pk, text="Bonjour")
    services.send(awa, conversation.pk, text="Vous êtes là ?")
    member = ConversationMember.objects.get(conversation=conversation, user=aicha)
    assert selectors.unread_messages(member).count() == 2
    assert selectors.unread_conversation_count(aicha) == 1
    assert selectors.unread_conversation_count(awa) == 0

    assert services.mark_delivered(aicha) == 1
    services.mark_read(aicha, conversation.pk)
    assert selectors.unread_conversation_count(aicha) == 0


def test_alerts_are_grouped_and_skipped_when_she_is_in_the_app(pair):
    awa, aicha, conversation = pair
    # Eager Celery: the alert runs at once, so mark the first one as already scheduled.
    member = ConversationMember.objects.get(conversation=conversation, user=aicha)
    ConversationMember.objects.filter(pk=member.pk).update(notify_scheduled=True)
    services.send(awa, conversation.pk, text="Bonjour")
    services.send(awa, conversation.pk, text="Vous êtes là ?")
    assert not Notification.objects.filter(user=aicha).exists()

    assert services.notify_unread(member.pk) is True
    alert = Notification.objects.get(user=aicha, event_key="messaging.new_messages")
    assert alert.data["count"] == 2 and alert.link == f"/messages/{conversation.pk}"

    realtime.mark_online(aicha.pk)
    services.send(awa, conversation.pk, text="Encore moi")
    assert Notification.objects.filter(user=aicha).count() == 1


def test_no_alert_for_a_muted_conversation(pair):
    awa, aicha, conversation = pair
    services.set_preferences(aicha, conversation.pk, muted=True)
    services.send(awa, conversation.pk, text="Bonjour")
    assert not Notification.objects.filter(user=aicha).exists()


def test_deleting_her_own_message(pair):
    awa, aicha, conversation = pair
    message = services.send(awa, conversation.pk, text="Oups")
    with pytest.raises(errors.NotYours):
        services.delete_message(aicha, message.pk)
    services.delete_message(awa, message.pk)
    message.refresh_from_db()
    assert message.deleted_at is not None


def test_reporting_a_message_reaches_the_moderation_queue(pair):
    awa, aicha, conversation = pair
    message = services.send(aicha, conversation.pk, text="Paie-moi en dehors")
    services.report_message(awa, message.pk, reason="scam")
    case = ModerationCase.objects.get(target_id=message.pk)
    assert case.author == aicha and "dehors" in case.excerpt
    with pytest.raises(errors.MessageNotFound):
        services.report_message(adult("Inès"), message.pk, reason="scam")
