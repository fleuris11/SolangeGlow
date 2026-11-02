"""Console clients: development and tests only. They log and keep an in-memory outbox."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger("solangeglow.providers")

# Last messages "sent", for tests and local inspection. Never used in production.
OUTBOX: list[dict] = []


def _mask(to: str) -> str:
    return f"{to[:4]}***{to[-2:]}"


class _ConsoleClient:
    """Refuses to exist where real providers are required (production)."""

    def __init__(self):
        if not settings.PROVIDERS_CONSOLE:
            raise ImproperlyConfigured("Console providers are forbidden here.")


class ConsoleWhatsAppClient(_ConsoleClient):
    name = "whatsapp"

    def send_template(self, to, template, language, parameters, *, button_code=None):
        OUTBOX.append(
            {"channel": "whatsapp", "to": to, "template": template, "parameters": parameters}
        )
        logger.warning("[DEV] WhatsApp template %s (%s) to %s", template, language, _mask(to))

    def send_text(self, to, body):
        OUTBOX.append({"channel": "whatsapp", "to": to, "body": body})
        logger.warning("[DEV] WhatsApp to %s: %s", _mask(to), body)


class ConsoleSmsClient(_ConsoleClient):
    name = "sms"

    def send(self, to, body):
        OUTBOX.append({"channel": "sms", "to": to, "body": body})
        logger.warning("[DEV] SMS to %s: %s", _mask(to), body)
