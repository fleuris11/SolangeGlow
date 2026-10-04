from apps.core.providers import ProviderError, ProviderNotConfigured
from apps.core.providers.clients import TwilioSmsClient

from .base import OtpDeliveryError, OtpMessage, OtpSender
from .texts import code_text


class SmsOtpSender(OtpSender):
    """SMS fallback, through Twilio. Another provider can replace it behind the same class."""

    channel = "sms"
    destination_kind = "phone"

    def is_available(self) -> bool:
        try:
            TwilioSmsClient()
        except ProviderNotConfigured:
            return False
        return True

    def send(self, message: OtpMessage) -> None:
        try:
            TwilioSmsClient().send(message.destination, code_text(message))
        except (ProviderError, ProviderNotConfigured) as exc:
            raise OtpDeliveryError(str(exc)) from exc
