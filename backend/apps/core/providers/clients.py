"""Real provider clients. No keys → `ProviderNotConfigured`."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings

from .base import ProviderError, ProviderNotConfigured

logger = logging.getLogger("solangeglow.providers")

GRAPH_URL = "https://graph.facebook.com/{version}/{phone_number_id}/messages"
TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _raise_for(provider: str, response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise ProviderError(f"{provider}: HTTP {response.status_code}")


class WhatsAppCloudClient:
    """WhatsApp Business Cloud API (Meta)."""

    name = "whatsapp"

    def __init__(self):
        if not (settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID):
            raise ProviderNotConfigured("whatsapp")

    def _post(self, payload: dict) -> None:
        url = GRAPH_URL.format(
            version=settings.WHATSAPP_API_VERSION,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        )
        try:
            response = httpx.post(
                url,
                json={"messaging_product": "whatsapp", **payload},
                headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("whatsapp: network error") from exc
        _raise_for("whatsapp", response)

    def send_template(self, to, template, language, parameters, *, button_code=None):
        components = [
            {"type": "body", "parameters": [{"type": "text", "text": p} for p in parameters]}
        ]
        if button_code:
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": button_code}],
                }
            )
        self._post(
            {
                "to": to.lstrip("+"),
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": language},
                    "components": components,
                },
            }
        )

    def send_text(self, to, body):
        # Free text only reaches people who wrote to us in the last 24 hours (Meta rule).
        self._post({"to": to.lstrip("+"), "type": "text", "text": {"body": body}})


class TwilioSmsClient:
    name = "sms"

    def __init__(self):
        if not (
            settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM
        ):
            raise ProviderNotConfigured("sms")

    def send(self, to, body):
        try:
            response = httpx.post(
                TWILIO_URL.format(sid=settings.TWILIO_ACCOUNT_SID),
                data={"To": to, "From": settings.TWILIO_FROM, "Body": body},
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise ProviderError("sms: network error") from exc
        _raise_for("sms", response)
