"""Which finished transactions open the right to a verified review (and a client rating).

The booking module (module 8) and the shop (module 4) each register a ReviewEligibility.
Until then no transaction exists, so nobody can review: that is the rule
« only a client who really booked or bought can rate ».
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Transaction:
    kind: str  # TransactionKind: "booking" or "order"
    id: uuid.UUID
    client_id: uuid.UUID
    pro_id: uuid.UUID
    finished_at: datetime.datetime | None  # None: not finished (no review yet)
    label: str  # what the client sees: « Knotless mi-dos, 12 octobre »


class ReviewEligibility(Protocol):
    kind: str

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        """The transaction, whatever its state, or None when it does not exist."""

    def finished_for_client(self, client_id: uuid.UUID) -> Iterable[Transaction]:
        """Finished transactions of a client (to suggest a review)."""

    def finished_for_pro(self, pro_id: uuid.UUID) -> Iterable[Transaction]:
        """Finished transactions of a pro (to rate her clients)."""


_PROVIDERS: dict[str, ReviewEligibility] = {}


def register(provider: ReviewEligibility) -> None:
    """Called by the booking and shop apps in their AppConfig.ready()."""
    _PROVIDERS[provider.kind] = provider


def unregister(kind: str) -> None:
    _PROVIDERS.pop(kind, None)


def provider_for(kind: str) -> ReviewEligibility | None:
    return _PROVIDERS.get(kind)


def all_providers() -> list[ReviewEligibility]:
    return list(_PROVIDERS.values())
