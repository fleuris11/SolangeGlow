import logging

import httpx
import pytest
import respx
from django.core import mail
from django.core.cache import cache

from apps.accounts.otp.base import OtpDeliveryError, OtpMessage
from apps.accounts.otp.console import DEV_CODE_CACHE_PREFIX, ConsoleOtpSender
from apps.accounts.otp.email import EmailOtpSender
from apps.accounts.otp.sms import SmsOtpSender
from apps.accounts.otp.whatsapp import WhatsAppOtpSender

MESSAGE = OtpMessage("+2290197123456", "482913", "fr", 10)


@pytest.fixture
def whatsapp_settings(settings):
    settings.WHATSAPP_ACCESS_TOKEN = "token"
    settings.WHATSAPP_PHONE_NUMBER_ID = "1234"
    settings.WHATSAPP_TEMPLATE_NAME = "solange_glow_code"
    settings.WHATSAPP_API_VERSION = "v23.0"
    return settings


@pytest.fixture
def twilio_settings(settings):
    settings.TWILIO_ACCOUNT_SID = "AC123"
    settings.TWILIO_AUTH_TOKEN = "secret"
    settings.TWILIO_FROM = "+15005550006"
    return settings


def test_whatsapp_is_unavailable_without_credentials(settings):
    settings.WHATSAPP_ACCESS_TOKEN = ""
    assert WhatsAppOtpSender().is_available() is False


@respx.mock
def test_whatsapp_sends_the_authentication_template(whatsapp_settings):
    route = respx.post("https://graph.facebook.com/v23.0/1234/messages").mock(
        return_value=httpx.Response(200, json={"messages": [{"id": "wamid"}]})
    )

    WhatsAppOtpSender().send(MESSAGE)

    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer token"
    body = httpx.Response(200, content=request.content).json()
    assert body["to"] == "2290197123456"
    assert body["template"]["name"] == "solange_glow_code"
    assert body["template"]["language"] == {"code": "fr"}
    assert body["template"]["components"][0]["parameters"][0]["text"] == "482913"


@respx.mock
def test_whatsapp_error_raises_delivery_error(whatsapp_settings):
    respx.post("https://graph.facebook.com/v23.0/1234/messages").mock(
        return_value=httpx.Response(400, json={"error": {"message": "bad"}})
    )

    with pytest.raises(OtpDeliveryError):
        WhatsAppOtpSender().send(MESSAGE)


@respx.mock
def test_whatsapp_network_error_raises_delivery_error(whatsapp_settings):
    respx.post("https://graph.facebook.com/v23.0/1234/messages").mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )

    with pytest.raises(OtpDeliveryError):
        WhatsAppOtpSender().send(MESSAGE)


@respx.mock
def test_sms_goes_through_twilio_in_the_right_language(twilio_settings):
    route = respx.post("https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json").mock(
        return_value=httpx.Response(201, json={"sid": "SM1"})
    )

    SmsOtpSender().send(MESSAGE)

    content = route.calls.last.request.content.decode()
    assert "To=%2B2290197123456" in content
    assert "482913" in content


def test_email_sender_sends_the_code(settings):
    EmailOtpSender().send(OtpMessage("awa@example.com", "482913", "en", 10))

    assert len(mail.outbox) == 1
    assert "482913" in mail.outbox[0].subject
    assert mail.outbox[0].to == ["awa@example.com"]


def test_console_sender_masks_the_destination(settings, caplog):
    settings.ACCOUNTS_DEV_OTP_ENDPOINT = False
    with caplog.at_level(logging.WARNING, logger="solangeglow.otp"):
        ConsoleOtpSender().send(MESSAGE)

    assert "482913" in caplog.text
    assert "0197123456" not in caplog.text
    assert cache.get(DEV_CODE_CACHE_PREFIX + MESSAGE.destination) is None


def test_console_sender_is_off_in_production_settings(settings):
    settings.ACCOUNTS_OTP_CONSOLE = False
    assert ConsoleOtpSender().is_available() is False


def test_console_sender_keeps_the_code_for_the_dev_endpoint(settings):
    settings.ACCOUNTS_DEV_OTP_ENDPOINT = True
    ConsoleOtpSender().send(MESSAGE)

    assert cache.get(DEV_CODE_CACHE_PREFIX + MESSAGE.destination) == "482913"
