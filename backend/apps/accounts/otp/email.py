from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail

from .base import OtpDeliveryError, OtpMessage, OtpSender
from .texts import code_text, email_subject


class EmailOtpSender(OtpSender):
    channel = "email"
    destination_kind = "email"

    def is_available(self) -> bool:
        return bool(settings.EMAIL_BACKEND)

    def send(self, message: OtpMessage) -> None:
        try:
            send_mail(
                email_subject(message),
                code_text(message),
                settings.DEFAULT_FROM_EMAIL,
                [message.destination],
            )
        except (SMTPException, OSError) as exc:
            raise OtpDeliveryError("email: delivery failed") from exc
