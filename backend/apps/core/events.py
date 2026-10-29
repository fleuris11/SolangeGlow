"""Events between modules: a module announces what happened, others listen.

The announcer never knows who listens (the shop does not import the games). A listener
runs after the commit of the announcer's transaction, and its failure is logged without
ever breaking the action that announced it (a payment is never refused because of points).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable

from django.db import transaction

logger = logging.getLogger("solangeglow.events")

_listeners: dict[str, list[Callable]] = defaultdict(list)


def subscribe(event: str, callback: Callable) -> None:
    if callback not in _listeners[event]:
        _listeners[event].append(callback)


def unsubscribe(event: str, callback: Callable) -> None:
    if callback in _listeners[event]:
        _listeners[event].remove(callback)


def _run(event: str, callback: Callable, payload: dict) -> None:
    try:
        with transaction.atomic():
            callback(**payload)
    except Exception:
        logger.exception("Listener of %s failed", event)


def emit(event: str, **payload) -> None:
    for callback in list(_listeners.get(event, ())):
        transaction.on_commit(lambda cb=callback: _run(event, cb, payload))
