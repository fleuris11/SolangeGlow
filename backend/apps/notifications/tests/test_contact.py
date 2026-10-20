"""Messages to guests (no account): WhatsApp first, SMS when WhatsApp cannot deliver."""

import pytest

from apps.core import providers
from apps.core.providers.base import ProviderError
from apps.notifications.models import ContactMessage, NotificationTemplate
from apps.notifications.services import deliver_contact, notify_contact

pytestmark = pytest.mark.django_db
PHONE = "+2290197000001"


@pytest.fixture
def templates():
    for channel in ("whatsapp", "sms"):
        NotificationTemplate.objects.create(
            event_key="test.guest",
            channel=channel,
            title="Bonjour",
            body="Rendez-vous {{ when }}",
            title_fr="Bonjour",
            body_fr="Rendez-vous {{ when }}",
        )


class Recorder:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send_text(self, phone, text):
        if self.fail:
            raise ProviderError("down")
        self.sent.append((phone, text))

    def send(self, phone, text):
        self.sent.append((phone, text))


def test_whatsapp_first(templates, monkeypatch):
    whatsapp = Recorder()
    monkeypatch.setattr(providers, "whatsapp_client", lambda: whatsapp)
    message = notify_contact(PHONE, "test.guest", {"when": "demain à 10 h"})
    message.refresh_from_db()
    assert message.channel == "whatsapp" and message.status == ContactMessage.Status.SENT
    assert whatsapp.sent == [(PHONE, "Bonjour\nRendez-vous demain à 10 h")]


def test_sms_when_whatsapp_fails(templates, monkeypatch):
    sms = Recorder()
    monkeypatch.setattr(providers, "whatsapp_client", lambda: Recorder(fail=True))
    monkeypatch.setattr(providers, "sms_client", lambda: sms)
    message = notify_contact(PHONE, "test.guest", {"when": "demain"})
    message.refresh_from_db()
    assert message.channel == "sms" and message.status == ContactMessage.Status.SENT
    assert message.attempts == 2 and sms.sent == [(PHONE, "Rendez-vous demain")]
    assert deliver_contact(str(message.pk)) == ContactMessage.Status.SENT  # once only


def test_nothing_without_number_or_template():
    assert notify_contact("", "test.guest") is None
    assert notify_contact(PHONE, "test.unknown") is None
