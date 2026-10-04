import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.audit.models import AuditEvent
from apps.core.audit.services import record, snapshot
from apps.core.models import PlatformSetting
from apps.core.providers import ProviderNotConfigured, sms_client, whatsapp_client
from apps.core.providers.console import OUTBOX, ConsoleSmsClient

from .factories import PlatformSettingFactory

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def owner():
    return User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")


@pytest.fixture
def admin_client(client, owner):
    client.force_login(owner)
    return client


# --- Audit ---------------------------------------------------------------------------


def test_snapshot_masks_sensitive_fields(owner):
    data = snapshot(owner)

    assert data["password"] == "***"
    assert data["email"] == "owner@example.com"


def test_audit_events_are_immutable(owner):
    event = record("test.action", owner, actor=owner)

    with pytest.raises(ValueError):
        event.save()


def test_admin_change_is_recorded_with_only_the_changed_fields(admin_client, owner):
    setting = PlatformSettingFactory(key="escrow.ship_deadline_days", value="3")
    url = reverse("admin:core_platformsetting_change", args=[setting.pk])

    response = admin_client.post(
        url,
        {
            "key": "escrow.ship_deadline_days",
            "value_type": "integer",
            "value": "5",
            "description_fr": "",
            "description_en": "",
            "description_sk": "",
        },
    )

    assert response.status_code == 302, response.content.decode()[:1500]
    event = AuditEvent.objects.get(action="admin.change")
    assert event.actor == owner
    assert event.before == {"value": "3"}
    assert event.after == {"value": "5"}
    assert event.target_id == str(setting.pk)


def test_admin_delete_is_recorded(admin_client):
    setting = PlatformSettingFactory(key="temporary.setting", value="1")

    admin_client.post(
        reverse("admin:core_platformsetting_delete", args=[setting.pk]), {"post": "yes"}
    )

    event = AuditEvent.objects.get(action="admin.delete")
    assert event.before["key"] == "temporary.setting"
    assert not PlatformSetting.objects.filter(pk=setting.pk).exists()


def test_suspending_from_the_admin_is_audited(admin_client, owner):
    awa = User.objects.create_user(phone="+2290197123456")

    admin_client.post(
        reverse("admin:accounts_user_changelist"),
        {"action": "suspend_users", "_selected_action": [awa.pk]},
    )

    event = AuditEvent.objects.get(action="account.suspended")
    assert event.actor == owner
    assert event.target_id == str(awa.pk)


def test_audit_journal_page_is_read_only(admin_client, owner):
    record("test.action", owner, actor=owner)

    assert admin_client.get(reverse("admin:core_auditevent_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:core_auditevent_add")).status_code == 403


# --- Providers -----------------------------------------------------------------------


def test_real_clients_need_keys(settings):
    settings.TWILIO_ACCOUNT_SID = ""
    settings.WHATSAPP_ACCESS_TOKEN = ""

    with pytest.raises(ProviderNotConfigured):
        sms_client(allow_console=False)
    with pytest.raises(ProviderNotConfigured):
        whatsapp_client(allow_console=False)


def test_console_clients_only_when_allowed(settings):
    settings.TWILIO_ACCOUNT_SID = ""
    settings.PROVIDERS_CONSOLE = True
    client = sms_client()
    assert isinstance(client, ConsoleSmsClient)
    client.send("+2290197123456", "Bonjour")
    assert OUTBOX[-1] == {"channel": "sms", "to": "+2290197123456", "body": "Bonjour"}

    settings.PROVIDERS_CONSOLE = False
    with pytest.raises(ProviderNotConfigured):
        sms_client()


def test_configured_client_is_used(settings):
    settings.TWILIO_ACCOUNT_SID = "AC1"
    settings.TWILIO_AUTH_TOKEN = "t"
    settings.TWILIO_FROM = "+15005550006"

    assert sms_client().__class__.__name__ == "TwilioSmsClient"
