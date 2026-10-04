from .base import OtpSender
from .console import ConsoleOtpSender
from .email import EmailOtpSender
from .sms import SmsOtpSender
from .whatsapp import WhatsAppOtpSender

SENDERS: dict[str, type[OtpSender]] = {
    sender.channel: sender
    for sender in (WhatsAppOtpSender, SmsOtpSender, EmailOtpSender, ConsoleOtpSender)
}


def get_sender(channel: str) -> OtpSender | None:
    sender_class = SENDERS.get(channel)
    return sender_class() if sender_class else None
