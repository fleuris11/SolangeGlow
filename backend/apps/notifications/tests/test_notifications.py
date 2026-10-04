import datetime
from zoneinfo import ZoneInfo

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.providers.console import OUTBOX
from apps.core.tests.factories import CountryFactory, CurrencyFactory
from apps.notifications import channels as notification_channels
from apps.notifications import quiet_hours, services, vapid
from apps.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationTemplate,
    PushSubscription,
)
from apps.notifications.tasks import deliver_notification

pytestmark = pytest.mark.django_db

DAYTIME = datetime.datetime(2026, 10, 5, 12, 0, tzinfo=datetime.UTC)


@pytest.fixture
def awa():
    benin = CountryFactory(code="BJ", timezone="Africa/Porto-Novo")
    return User.objects.create_user(
        phone="+2290197123456",
        email="awa@example.com",
        first_name="Awa",
        country=benin,
        preferred_language="fr",
    )


@pytest.fixture
def daytime(monkeypatch):
    monkeypatch.setattr("apps.notifications.services.timezone.now", lambda: DAYTIME)
    return DAYTIME


@pytest.fixture
def push_sent(monkeypatch):
    sent = []

    def fake_webpush(subscription_info, data, **kwargs):
        sent.append({"endpoint": subscription_info["endpoint"], "data": data})

    monkeypatch.setattr(notification_channels, "webpush", fake_webpush)
    return sent


@pytest.fixture
def vapid_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(vapid, "DEV_KEYS_FILE", tmp_path / "vapid.json")
    vapid.keys.cache_clear()
    yield
    vapid.keys.cache_clear()


def subscribe(user, endpoint="https://push.example.com/abc"):
    return PushSubscription.objects.create(user=user, endpoint=endpoint, p256dh="k", auth="a")


# --- notify --------------------------------------------------------------------------


def test_welcome_creates_an_in_app_notification_in_her_language(awa, daytime):
    notification = services.notify(awa, "account.welcome")

    assert notification.in_app is True
    assert notification.title == "Bienvenue sur Solange Glow !"
    assert notification.link == "/"
    assert services.unread_count(awa) == 1


def test_texts_follow_the_language_of_the_person(awa, daytime):
    awa.preferred_language = "sk"
    awa.save()

    notification = services.notify(awa, "account.welcome")

    assert notification.title == "Vitaj v Solange Glow!"


def test_context_fills_the_template(awa, daytime):
    notification = services.notify(awa, "account.contact_changed", {"contact": "aw***@x.com"})

    assert "aw***@x.com" in notification.body


def test_email_is_sent_when_accepted(awa, daytime):
    services.notify(awa, "account.welcome")

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Bienvenue sur Solange Glow !"
    assert "http://localhost:3000/fr/" in mail.outbox[0].body
    delivery = NotificationDelivery.objects.get(channel="email")
    assert delivery.status == "sent"


def test_preferences_are_respected(awa, daytime):
    awa.notify_email = False
    awa.save()

    services.notify(awa, "account.welcome")

    assert mail.outbox == []
    assert not NotificationDelivery.objects.filter(channel="email").exists()


def test_inactive_channels_and_unknown_events_send_nothing(awa, daytime):
    assert services.notify(awa, "no.such_event") is None
    services.notify(awa, "account.welcome")
    assert not NotificationDelivery.objects.filter(channel__in=["whatsapp", "sms"]).exists()


def test_whatsapp_goes_through_the_console_client_in_development(awa, daytime):
    NotificationTemplate.objects.filter(event_key="account.welcome", channel="whatsapp").update(
        is_active=True
    )

    services.notify(awa, "account.welcome")

    assert OUTBOX[-1]["channel"] == "whatsapp"
    assert OUTBOX[-1]["to"] == "+2290197123456"


def test_missing_provider_is_skipped_not_failed(awa, daytime, settings):
    settings.PROVIDERS_CONSOLE = False
    NotificationTemplate.objects.filter(event_key="account.welcome", channel="sms").update(
        is_active=True
    )

    services.notify(awa, "account.welcome")

    delivery = NotificationDelivery.objects.get(channel="sms")
    assert delivery.status == "skipped"


def test_deleted_or_inactive_people_get_nothing(awa, daytime):
    awa.is_active = False
    awa.save()

    assert services.notify(awa, "account.welcome") is None


# --- Push ----------------------------------------------------------------------------


def test_push_is_sent_to_every_device(awa, daytime, push_sent, vapid_keys):
    subscribe(awa, "https://push.example.com/phone")
    subscribe(awa, "https://push.example.com/laptop")

    services.notify(awa, "system.test")

    assert len(push_sent) == 2
    assert '"url": "/fr/notifications"' in push_sent[0]["data"]
    assert NotificationDelivery.objects.get(channel="push").status == "sent"


def test_expired_push_subscription_is_removed(awa, daytime, monkeypatch, vapid_keys):
    from pywebpush import WebPushException

    class Gone:
        status_code = 410

    def gone(**kwargs):
        raise WebPushException("gone", response=Gone())

    monkeypatch.setattr(notification_channels, "webpush", gone)
    subscribe(awa)

    services.notify(awa, "system.test")

    assert not PushSubscription.objects.exists()


def test_failed_channel_is_retried_then_marked_failed(awa, daytime, monkeypatch, push_sent):
    from celery.exceptions import Retry

    from apps.core.providers import ProviderError

    def broken(delivery):
        raise ProviderError("down")

    monkeypatch.setitem(services.SENDERS, "email", broken)
    monkeypatch.setattr(
        "apps.notifications.tasks.deliver_notification.apply_async", lambda **kw: None
    )
    services.notify(awa, "account.welcome")
    delivery = NotificationDelivery.objects.get(channel="email")

    with pytest.raises(Retry):
        deliver_notification.apply(args=[str(delivery.pk)])
    assert deliver_notification.apply(args=[str(delivery.pk)], retries=4).get() == "failed"
    delivery.refresh_from_db()
    assert delivery.status == "failed"


# --- Quiet hours ---------------------------------------------------------------------


def test_night_alerts_wait_for_the_morning(awa, monkeypatch, push_sent, vapid_keys):
    night = datetime.datetime(2026, 10, 5, 23, 30, tzinfo=ZoneInfo("Africa/Porto-Novo"))
    monkeypatch.setattr("apps.notifications.services.timezone.now", lambda: night)
    monkeypatch.setattr(
        "apps.notifications.tasks.deliver_notification.apply_async", lambda **kw: None
    )
    subscribe(awa)

    services.notify(awa, "system.test")

    delivery = NotificationDelivery.objects.get(channel="push")
    local = delivery.scheduled_for.astimezone(ZoneInfo("Africa/Porto-Novo"))
    assert (local.date(), local.hour, local.minute) == (datetime.date(2026, 10, 6), 7, 0)


def test_quiet_hours_window_and_personal_override(awa):
    zone = ZoneInfo("Africa/Porto-Novo")
    morning = datetime.datetime(2026, 10, 5, 6, 0, tzinfo=zone)
    noon = datetime.datetime(2026, 10, 5, 12, 0, tzinfo=zone)

    assert quiet_hours.next_allowed(awa, noon) == noon
    assert quiet_hours.next_allowed(awa, morning).astimezone(zone).hour == 7

    awa.quiet_hours_start = datetime.time(12, 0)
    awa.quiet_hours_end = datetime.time(14, 0)
    assert quiet_hours.next_allowed(awa, noon).astimezone(zone).hour == 14
    assert quiet_hours.next_allowed(awa, morning) == morning


def test_quiet_hours_follow_the_country_time_zone():
    france = CountryFactory(
        code="FR", timezone="Europe/Paris", default_currency=CurrencyFactory(code="EUR")
    )
    clarisse = User.objects.create_user(email="c@example.com", country=france)
    late_in_cotonou = datetime.datetime(2026, 10, 5, 21, 30, tzinfo=datetime.UTC)  # 23:30 Paris

    assert quiet_hours.next_allowed(clarisse, late_in_cotonou) != late_in_cotonou


# --- API -----------------------------------------------------------------------------


@pytest.fixture
def client(awa):
    api = APIClient()
    api.force_authenticate(awa)
    return api


def test_list_and_mark_read(client, awa, daytime):
    first = services.notify(awa, "account.welcome")
    services.notify(awa, "system.test")

    response = client.get(reverse("v1:notifications"))
    events = sorted(n["event_key"] for n in response.json()["results"])
    assert events == ["account.welcome", "system.test"]
    assert client.get(reverse("v1:notifications-unread")).json() == {"unread": 2}

    response = client.post(
        reverse("v1:notifications-read"), {"ids": [str(first.pk)]}, format="json"
    )
    assert response.json() == {"unread": 1}
    response = client.post(reverse("v1:notifications-read"), {}, format="json")
    assert response.json() == {"unread": 0}


def test_people_only_see_their_notifications(client, daytime):
    other = User.objects.create_user(email="o@example.com")
    services.notify(other, "account.welcome")

    assert client.get(reverse("v1:notifications")).json()["results"] == []


def test_push_subscription_api(client, awa, vapid_keys):
    key = client.get(reverse("v1:push-key")).json()["public_key"]
    assert len(key) > 80  # uncompressed P-256 point, base64url

    body = {"endpoint": "https://push.example.com/x", "keys": {"p256dh": "p", "auth": "a"}}
    assert client.post(reverse("v1:push-subscribe"), body, format="json").status_code == 201
    assert PushSubscription.objects.filter(user=awa).count() == 1

    client.post(reverse("v1:push-unsubscribe"), {"endpoint": body["endpoint"]}, format="json")
    assert not PushSubscription.objects.exists()


def test_test_notification_endpoint(client, awa, daytime):
    assert client.post(reverse("v1:notifications-test")).status_code == 202
    assert Notification.objects.get(user=awa).event_key == "system.test"


# --- Real time -----------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_websocket_sends_the_unread_counter():
    from config.asgi import application

    benin = CountryFactory(code="BJ", timezone="Africa/Porto-Novo")
    user = User.objects.create_user(phone="+2290197123456", country=benin)
    token = str(RefreshToken.for_user(user).access_token)

    async def scenario():
        communicator = WebsocketCommunicator(
            application,
            "/ws/notifications/",
            headers=[(b"cookie", f"sg_access={token}".encode()), (b"origin", b"http://localhost")],
        )
        connected, _ = await communicator.connect()
        assert connected
        first = await communicator.receive_json_from()
        await communicator.disconnect()
        return first

    assert async_to_sync(scenario)() == {"type": "unread", "unread": 0}


@pytest.mark.django_db(transaction=True)
def test_websocket_refuses_visitors():
    from config.asgi import application

    async def scenario():
        communicator = WebsocketCommunicator(
            application, "/ws/notifications/", headers=[(b"origin", b"http://localhost")]
        )
        connected, _ = await communicator.connect()
        return connected

    assert async_to_sync(scenario)() is False


def test_seeded_templates_exist_in_three_languages():
    template = NotificationTemplate.objects.get(event_key="account.welcome", channel="in_app")

    assert template.title_fr and template.title_en and template.title_sk
    assert timezone.now()
