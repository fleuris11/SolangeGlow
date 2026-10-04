"""Console clients: development and tests only. They log and keep an in-memory outbox."""

from __future__ import annotations

import logging

logger = logging.getLogger("solangeglow.providers")

# Last messages "sent", for tests and local inspection. Never used in production.
OUTBOX: list[dict] = []


def _mask(to: str) -> str:
    return f"{to[:4]}***{to[-2:]}"


class ConsoleWhatsAppClient:
    name = "whatsapp"

    def send_template(self, to, template, language, parameters, *, button_code=None):
        OUTBOX.append(
            {"channel": "whatsapp", "to": to, "template": template, "parameters": parameters}
        )
        logger.warning("[DEV] WhatsApp template %s (%s) to %s", template, language, _mask(to))

    def send_text(self, to, body):
        OUTBOX.append({"channel": "whatsapp", "to": to, "body": body})
        logger.warning("[DEV] WhatsApp to %s: %s", _mask(to), body)


class ConsoleSmsClient:
    name = "sms"

    def send(self, to, body):
        OUTBOX.append({"channel": "sms", "to": to, "body": body})
        logger.warning("[DEV] SMS to %s: %s", _mask(to), body)
