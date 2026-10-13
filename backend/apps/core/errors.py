"""Business errors raised by services and turned into the API error format."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """An expected refusal: what happened (code) and what to do (translated message)."""

    code = "error"
    message: Any = ""
    status_code = 400

    def __init__(self, message: Any = None, *, details: dict | None = None):
        if message is not None:
            self.message = message
        self.details = details or {}
        super().__init__(str(self.message))

    def text(self) -> str:
        """The translated message with its details filled in (« 4 attempts left »)."""
        message = str(self.message)
        if not self.details:
            return message
        try:
            return message % self.details
        except (KeyError, TypeError, ValueError):
            return message
