"""Production readiness: what refuses to start, the admin banner, the first start."""

import os
import subprocess
import sys
from io import StringIO

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import CommandError, call_command
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.otp.base import OtpMessage
from apps.accounts.otp.console import ConsoleOtpSender
from apps.accounts.otp.email import EmailOtpSender
from apps.core import readiness
from apps.core.providers.console import ConsoleSmsClient, ConsoleWhatsAppClient
from config.prod_checks import unsafe_settings

SAFE = {
    "secret_key": "s" * 50,
    "allowed_hosts": ["solangeglow.com"],
    "site_url": "https://solangeglow.com",
    "internal_token": "t" * 50,
    "vault_key": "vault",
    "bucket": "media",
    "environ": {},
}
PROD_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "s" * 50,
    "DJANGO_ALLOWED_HOSTS": "solangeglow.com",
    "SITE_URL": "https://solangeglow.com",
    "INTERNAL_API_TOKEN": "t" * 50,
    "IDENTITY_VAULT_KEY": "vault",
    "AWS_STORAGE_BUCKET_NAME": "media",
    "DATABASE_URL": "postgis://u:p@localhost/x",
}


def _load_prod(**extra):
    """Imports the production settings in a fresh process, like a server starting."""
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "PYTHONPATH")}
    code = (
        "import django; from django.conf import settings; django.setup();"
        "print(settings.DEBUG, settings.AUTH_COOKIES['SECURE'], settings.PROVIDERS_CONSOLE,"
        " settings.ACCOUNTS_OTP_CONSOLE, settings.PAYMENTS_FAKE_ENABLED,"
        " settings.DATABASES['default']['CONN_MAX_AGE'], settings.API_DOCS_PUBLIC,"
        " 'daphne' in settings.INSTALLED_APPS, settings.BACKOFFICE_REQUIRE_2FA)"
    )
    return subprocess.run(  # noqa: S603 (fixed command, this very Python)
        [sys.executable, "-c", code],
        env={**env, **PROD_ENV, **extra},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_safe_settings_have_no_problem():
    assert unsafe_settings(**SAFE) == []


@pytest.mark.parametrize(
    "change, named",
    [
        ({"secret_key": "short"}, "DJANGO_SECRET_KEY"),
        ({"secret_key": "dev-only-insecure-secret-key-change-me" * 2}, "DJANGO_SECRET_KEY"),
        ({"internal_token": ""}, "INTERNAL_API_TOKEN"),
        ({"allowed_hosts": []}, "DJANGO_ALLOWED_HOSTS"),
        ({"allowed_hosts": ["*"]}, "DJANGO_ALLOWED_HOSTS"),
        ({"site_url": "http://solangeglow.com"}, "SITE_URL"),
        ({"vault_key": ""}, "IDENTITY_VAULT_KEY"),
        ({"bucket": ""}, "AWS_STORAGE_BUCKET_NAME"),
        ({"environ": {"PROVIDERS_CONSOLE": "true"}}, "PROVIDERS_CONSOLE"),
        ({"environ": {"ACCOUNTS_OTP_CONSOLE": "1"}}, "ACCOUNTS_OTP_CONSOLE"),
        ({"environ": {"PAYMENTS_FAKE_ENABLED": "yes"}}, "PAYMENTS_FAKE_ENABLED"),
        ({"environ": {"DJANGO_DEBUG": "True"}}, "DJANGO_DEBUG"),
    ],
)
def test_each_unsafe_setting_is_named(change, named):
    problems = unsafe_settings(**{**SAFE, **change})
    assert any(named in problem for problem in problems)


def test_production_settings_force_every_shortcut_off():
    run = _load_prod()
    assert run.returncode == 0, run.stderr
    assert run.stdout.split() == [
        "False",  # DEBUG
        "True",  # secure cookies
        "False",  # console providers
        "False",  # console codes
        "False",  # test payments
        "0",  # no kept database connection under ASGI
        "False",  # no public API description
        "False",  # no Daphne
        "True",  # two-factor sign-in of the team
    ]


def test_production_refuses_to_start_when_unsafe():
    run = _load_prod(DJANGO_SECRET_KEY="short", PROVIDERS_CONSOLE="true")
    assert run.returncode != 0
    assert "DJANGO_SECRET_KEY" in run.stderr
    assert "PROVIDERS_CONSOLE" in run.stderr


@override_settings(PROVIDERS_CONSOLE=False)
def test_console_clients_cannot_exist_in_production():
    with pytest.raises(ImproperlyConfigured):
        ConsoleSmsClient()
    with pytest.raises(ImproperlyConfigured):
        ConsoleWhatsAppClient()


@override_settings(ACCOUNTS_OTP_CONSOLE=False)
def test_console_code_sender_is_off_and_refuses_in_production():
    sender = ConsoleOtpSender()
    assert sender.is_available() is False
    with pytest.raises(ImproperlyConfigured):
        sender.send(
            OtpMessage(destination="+22997000000", code="123456", locale="fr", ttl_minutes=5)
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="",
)
def test_email_codes_are_off_without_an_smtp_server():
    assert EmailOtpSender().is_available() is False
    with override_settings(EMAIL_HOST="smtp.example.com"):
        assert EmailOtpSender().is_available() is True


NOTHING_CONNECTED = {name: "" for check in readiness.CHECKS for name in check.variables}


@override_settings(**NOTHING_CONNECTED, PROVIDERS_CONSOLE=False, PAYMENTS_FAKE_ENABLED=False)
def test_readiness_lists_everything_missing_most_serious_first():
    found = readiness.missing()
    levels = [entry["level"] for entry in found["entries"]]
    assert levels[:2] == [readiness.Level.BLOCKING, readiness.Level.BLOCKING]
    assert levels[-1] == readiness.Level.OPTIONAL
    assert {"payments_bj", "payments_fr", "whatsapp", "sms", "moderation_ai"} <= {
        entry["key"] for entry in found["entries"]
    }
    assert found["no_sign_in"] is True
    assert found["simulated"] is False


@override_settings(**{**NOTHING_CONNECTED, "EMAIL_HOST": "smtp.example.com"})
def test_one_channel_is_enough_to_sign_in():
    found = readiness.missing()
    assert found["no_sign_in"] is False
    assert "email" not in {entry["key"] for entry in found["entries"]}


@pytest.mark.django_db
@override_settings(**NOTHING_CONNECTED, PROVIDERS_CONSOLE=False, PAYMENTS_FAKE_ENABLED=False)
def test_admin_home_shows_the_banner_to_the_owner_only():
    owner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
    client = Client()
    client.force_login(owner)
    page = client.get(reverse("admin:index")).content.decode()
    assert 'id="readiness"' in page
    assert "FEDAPAY_SECRET_KEY" in page
    assert "TWILIO_ACCOUNT_SID" in page

    staff = User.objects.create_user(email="staff@example.com", password="x" * 12, is_staff=True)
    client.force_login(staff)
    assert 'id="readiness"' not in client.get(reverse("admin:index")).content.decode()


@pytest.mark.django_db
def test_health_deep_checks_database_and_cache():
    answer = Client().get("/api/v1/health?deep=1")
    assert answer.status_code == 200
    assert answer.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_deep_answers_503_when_the_database_is_down(monkeypatch):
    class Down:
        def cursor(self):
            raise ConnectionError

    monkeypatch.setattr("apps.core.api.views.connection", Down())
    assert Client().get("/api/v1/health?deep=1").status_code == 503
    assert Client().get("/api/v1/health").status_code == 200


@pytest.mark.django_db
def test_init_production_prepares_everything_without_demo_data():
    out = StringIO()
    call_command("init_production", admin_email="Owner@Example.com", stdout=out)
    text = out.getvalue()

    admin = User.objects.get(email="owner@example.com")
    assert admin.is_superuser and admin.is_staff
    password = text.split("shown only this once):")[1].split()[0]
    assert admin.check_password(password)
    assert "init_production: done." in text
    # No demo data: the only account is the admin.
    assert User.objects.filter(is_superuser=False).count() == 0
    assert not User.objects.filter(email__endswith="solangeglow.test").exists()


@pytest.mark.django_db
def test_init_production_can_run_again_and_keeps_the_admin():
    call_command("init_production", admin_email="owner@example.com", stdout=StringIO())
    before = User.objects.get(email="owner@example.com").password
    out = StringIO()
    call_command("init_production", stdout=out)
    assert "already there" in out.getvalue()
    assert "shown only this once" not in out.getvalue()
    assert User.objects.get(email="owner@example.com").password == before


@pytest.mark.django_db
def test_init_production_needs_an_admin_email_the_first_time():
    with pytest.raises(CommandError):
        call_command("init_production", stdout=StringIO())


@pytest.mark.django_db
def test_init_production_takes_the_password_from_the_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "from-the-environment-123")
    out = StringIO()
    call_command("init_production", admin_email="owner@example.com", stdout=out)
    assert "from-the-environment-123" not in out.getvalue()
    assert User.objects.get(email="owner@example.com").check_password("from-the-environment-123")


@pytest.mark.django_db
def test_admin_home_says_payment_is_closed_and_where_to_open_it():
    from apps.core.models import FeatureFlag

    owner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
    client = Client()
    client.force_login(owner)
    assert 'id="payments-switch"' not in client.get(reverse("admin:index")).content.decode()

    flag, _ = FeatureFlag.objects.update_or_create(
        key="payments_closed", defaults={"name": "Payments closed", "is_enabled": True}
    )
    page = client.get(reverse("admin:index")).content.decode()
    assert 'id="payments-switch"' in page
    assert reverse("admin:core_featureflag_change", args=[flag.pk]) in page
