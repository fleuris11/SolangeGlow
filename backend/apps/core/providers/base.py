from __future__ import annotations

from typing import Protocol


class ProviderNotConfigured(Exception):
    """The provider has no credentials: the caller skips it or fails clearly."""


class ProviderError(Exception):
    """The provider answered with an error or could not be reached (worth retrying)."""


class SmsClient(Protocol):
    name: str

    def send(self, to: str, body: str) -> None: ...


class WhatsAppClient(Protocol):
    name: str

    def send_template(
        self,
        to: str,
        template: str,
        language: str,
        parameters: list[str],
        *,
        button_code: str | None = None,
    ) -> None: ...

    def send_text(self, to: str, body: str) -> None: ...
