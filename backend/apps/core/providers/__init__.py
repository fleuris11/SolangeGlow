"""External providers behind small interfaces (ADR-003).

Real clients raise `ProviderNotConfigured` without keys; console clients log instead and
are only allowed when `settings.PROVIDERS_CONSOLE` is on (development and tests).
"""

from .base import ProviderError, ProviderNotConfigured
from .registry import sms_client, whatsapp_client

__all__ = ["ProviderError", "ProviderNotConfigured", "sms_client", "whatsapp_client"]
