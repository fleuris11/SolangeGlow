import httpx
from django.conf import settings

from .base import OtpDeliveryError, OtpMessage, OtpSender

GRAPH_URL = "https://graph.facebook.com/{version}/{phone_number_id}/messages"


class WhatsAppOtpSender(OtpSender):
    """WhatsApp Business Cloud API, with an approved "authentication" template.

    The template has one body variable (the code) and a "copy code" button that also
    receives the code. One template per language (fr, en, sk), same name.
    """

    channel = "whatsapp"
    destination_kind = "phone"

    def is_available(self) -> bool:
        return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    def payload(self, message: OtpMessage) -> dict:
        return {
            "messaging_product": "whatsapp",
            "to": message.destination.lstrip("+"),
            "type": "template",
            "template": {
                "name": settings.WHATSAPP_TEMPLATE_NAME,
                "language": {"code": message.locale},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": message.code}]},
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": message.code}],
                    },
                ],
            },
        }

    def send(self, message: OtpMessage) -> None:
        url = GRAPH_URL.format(
            version=settings.WHATSAPP_API_VERSION,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        )
        try:
            response = httpx.post(
                url,
                json=self.payload(message),
                headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
                timeout=settings.OTP_HTTP_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise OtpDeliveryError("whatsapp: network error") from exc
        if response.status_code >= 400:
            raise OtpDeliveryError(f"whatsapp: HTTP {response.status_code}")
