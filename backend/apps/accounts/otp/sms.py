import httpx
from django.conf import settings

from .base import OtpDeliveryError, OtpMessage, OtpSender
from .texts import code_text

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class SmsOtpSender(OtpSender):
    """SMS fallback, through Twilio. Another provider can replace it behind the same class."""

    channel = "sms"
    destination_kind = "phone"

    def is_available(self) -> bool:
        return bool(
            settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM
        )

    def send(self, message: OtpMessage) -> None:
        try:
            response = httpx.post(
                TWILIO_URL.format(sid=settings.TWILIO_ACCOUNT_SID),
                data={
                    "To": message.destination,
                    "From": settings.TWILIO_FROM,
                    "Body": code_text(message),
                },
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=settings.OTP_HTTP_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise OtpDeliveryError("sms: network error") from exc
        if response.status_code >= 400:
            raise OtpDeliveryError(f"sms: HTTP {response.status_code}")
