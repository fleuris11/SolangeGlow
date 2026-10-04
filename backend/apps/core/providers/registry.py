from django.conf import settings

from .base import ProviderNotConfigured, SmsClient, WhatsAppClient
from .clients import TwilioSmsClient, WhatsAppCloudClient
from .console import ConsoleSmsClient, ConsoleWhatsAppClient


def whatsapp_client(*, allow_console: bool = True) -> WhatsAppClient:
    """Real client when configured, console client in development, else ProviderNotConfigured."""
    try:
        return WhatsAppCloudClient()
    except ProviderNotConfigured:
        if allow_console and settings.PROVIDERS_CONSOLE:
            return ConsoleWhatsAppClient()
        raise


def sms_client(*, allow_console: bool = True) -> SmsClient:
    try:
        return TwilioSmsClient()
    except ProviderNotConfigured:
        if allow_console and settings.PROVIDERS_CONSOLE:
            return ConsoleSmsClient()
        raise
