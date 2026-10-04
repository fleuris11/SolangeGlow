import pytest

from apps.accounts.otp.base import OtpDeliveryError, OtpSender

CODE = "123456"
BENIN_PHONE = "+2290197123456"
FRANCE_PHONE = "+33612345678"


@pytest.fixture
def fixed_code(monkeypatch):
    """Every generated code is 123456."""
    monkeypatch.setattr("apps.accounts.services.secrets.randbelow", lambda _n: int(CODE))
    return CODE


class RecordingSender(OtpSender):
    """Test double: remembers what it sent, or fails on demand."""

    def __init__(self, channel, kind="phone", available=True, fails=False):
        self.channel = channel
        self.destination_kind = kind
        self.available = available
        self.fails = fails
        self.sent = []

    def is_available(self):
        return self.available

    def send(self, message):
        if self.fails:
            raise OtpDeliveryError(f"{self.channel} down")
        self.sent.append(message)


@pytest.fixture
def senders(monkeypatch, settings):
    """Replaces the real senders; console is off so only these are used."""
    settings.ACCOUNTS_OTP_CONSOLE = False
    registry = {
        "whatsapp": RecordingSender("whatsapp"),
        "sms": RecordingSender("sms"),
        "email": RecordingSender("email", kind="email"),
    }
    monkeypatch.setattr("apps.accounts.services.get_sender", lambda channel: registry.get(channel))
    return registry
