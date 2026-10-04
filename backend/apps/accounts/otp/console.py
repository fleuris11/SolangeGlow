import logging

from django.conf import settings
from django.core.cache import cache

from .base import OtpMessage, OtpSender

logger = logging.getLogger("solangeglow.otp")

DEV_CODE_CACHE_PREFIX = "dev:otp:"


def mask(destination: str) -> str:
    if "@" in destination:
        name, _, domain = destination.partition("@")
        return f"{name[:2]}***@{domain}"
    return f"{destination[:4]}***{destination[-2:]}"


class ConsoleOtpSender(OtpSender):
    """Development only: prints the code in the backend logs."""

    channel = "console"
    destination_kind = "any"

    def is_available(self) -> bool:
        return bool(settings.ACCOUNTS_OTP_CONSOLE)

    def send(self, message: OtpMessage) -> None:
        # The only place a code is ever logged, and it is disabled in production.
        logger.warning("[DEV] One-time code for %s: %s", mask(message.destination), message.code)
        if settings.ACCOUNTS_DEV_OTP_ENDPOINT:
            cache.set(
                DEV_CODE_CACHE_PREFIX + message.destination,
                message.code,
                message.ttl_minutes * 60,
            )
