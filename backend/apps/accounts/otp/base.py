"""Sending one-time codes. Each channel is an `OtpSender`; the order is a platform setting."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class OtpDeliveryError(Exception):
    """The code could not be delivered on this channel; the next channel is tried."""


@dataclass(frozen=True)
class OtpMessage:
    destination: str
    """E.164 phone number ("+22901970000000") or lowercase e-mail address."""
    code: str
    locale: str
    ttl_minutes: int


class OtpSender(ABC):
    channel: str
    """Value of `OtpChannel` this sender implements."""
    destination_kind: str
    """"phone" or "email"."""

    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider is configured. Unavailable senders are skipped."""

    @abstractmethod
    def send(self, message: OtpMessage) -> None:
        """Deliver the code or raise `OtpDeliveryError`. Never log the code."""
