from django.conf import settings

from apps.core.providers import ProviderError, ProviderNotConfigured
from apps.core.providers.clients import WhatsAppCloudClient

from .base import OtpDeliveryError, OtpMessage, OtpSender


class WhatsAppOtpSender(OtpSender):
    """WhatsApp Business Cloud API, with an approved "authentication" template.

    The template has one body variable (the code) and a "copy code" button that also
    receives the code. One template per language (fr, en, sk), same name.
    """

    channel = "whatsapp"
    destination_kind = "phone"

    def is_available(self) -> bool:
        try:
            WhatsAppCloudClient()
        except ProviderNotConfigured:
            return False
        return True

    def send(self, message: OtpMessage) -> None:
        try:
            WhatsAppCloudClient().send_template(
                message.destination,
                settings.WHATSAPP_TEMPLATE_NAME,
                message.locale,
                [message.code],
                button_code=message.code,
            )
        except (ProviderError, ProviderNotConfigured) as exc:
            raise OtpDeliveryError(str(exc)) from exc
