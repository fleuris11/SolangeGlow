"""Sources of lives: each module that plans lives registers one (academy: training, shop:
sale). The live room asks it who hosts, who may watch, ask or speak, and who sees the
replay; the module hears when its live starts and ends."""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Planned:
    """What the room needs to know about a planned live."""

    source_id: object
    title: str
    host: object  # the user who broadcasts
    pro: object | None
    country: object
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    cancelled: bool
    link: str  # the page of the live in its module (waiting room, shop)
    cover_url: str = ""


class LiveSource:
    kind = ""
    hands = False  # « Raise my hand » (training lives)
    guests = False  # watching without an account (sales lives)

    def planned(self, source_id) -> Planned | None:  # pragma: no cover - interface
        raise NotImplementedError

    def can_watch(self, user, source_id) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def replay_days(self, country) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def can_replay(self, user, source_id) -> bool:
        return self.can_watch(user, source_id)

    def started(self, source_id, room) -> None:
        """On air (notify, change its own status)."""

    def ended(self, source_id, room) -> None:
        """Over (change its own status)."""

    def extras(self, source_id, room, user) -> dict | None:
        """What the module adds to the room (pinned products of a sale…)."""
        return None

    def upcoming(self, country, now, limit: int) -> list[Planned]:
        return []

    def count_in_month(self, pro, start, end) -> int:
        """Lives of this pro planned in [start, end) (monthly free lives)."""
        return 0


_sources: dict[str, LiveSource] = {}


def register(source: LiveSource) -> None:
    _sources[source.kind] = source


def get(kind: str) -> LiveSource | None:
    return _sources.get(kind)


def all_sources() -> list[LiveSource]:
    return list(_sources.values())
