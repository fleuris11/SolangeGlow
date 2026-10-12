"""Live events of the messaging (Channels groups) and who is online (cache).

Each signed-in person has one group, joined by all her open tabs and phones. Events:
message, receipt (received / read), typing, presence, conversation (request accepted…),
unread (number of conversations with unread messages).
"""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("solangeglow.messaging")

# A device says "I am here" every 30 seconds; without news for 75 seconds, she is away.
ONLINE_SECONDS = 75
LAST_SEEN_SECONDS = 60 * 60 * 24 * 30


def group_name(user_id) -> str:
    return f"messaging.{user_id}"


def send_to(user_ids, event: dict) -> None:
    """Sends an event to every device of these people. Never fails the caller."""
    layer = get_channel_layer()
    if layer is None:
        return
    for user_id in {str(u) for u in user_ids}:
        try:
            async_to_sync(layer.group_send)(group_name(user_id), {"type": "relay", "event": event})
        except Exception:
            logger.warning("Real-time event failed", exc_info=True)


# --- Presence -------------------------------------------------------------------------------


def _online_key(user_id) -> str:
    return f"messaging:online:{user_id}"


def _seen_key(user_id) -> str:
    return f"messaging:seen:{user_id}"


def _viewing_key(user_id) -> str:
    return f"messaging:viewing:{user_id}"


def _devices_key(user_id) -> str:
    return f"messaging:devices:{user_id}"


def device_connected(user_id) -> int:
    """Number of her open devices (tabs, phones) after this one connected."""
    key = _devices_key(user_id)
    cache.add(key, 0, 6 * 3600)  # a counter lost in a crash does not last
    return cache.incr(key)


def device_disconnected(user_id) -> int:
    key = _devices_key(user_id)
    try:
        remaining = cache.decr(key)
    except ValueError:
        return 0
    if remaining <= 0:
        cache.delete(key)
    return max(remaining, 0)


def mark_online(user_id) -> None:
    now = timezone.now().isoformat()
    cache.set(_online_key(user_id), now, ONLINE_SECONDS)
    cache.set(_seen_key(user_id), now, LAST_SEEN_SECONDS)


def mark_offline(user_id) -> None:
    cache.delete(_online_key(user_id))
    cache.delete(_viewing_key(user_id))
    cache.set(_seen_key(user_id), timezone.now().isoformat(), LAST_SEEN_SECONDS)


def is_online(user_id) -> bool:
    return cache.get(_online_key(user_id)) is not None


def last_seen(user_id) -> str | None:
    return cache.get(_seen_key(user_id))


def set_viewing(user_id, conversation_id) -> None:
    """The conversation open on her screen: no notification for its new messages."""
    if conversation_id:
        cache.set(_viewing_key(user_id), str(conversation_id), ONLINE_SECONDS)
    else:
        cache.delete(_viewing_key(user_id))


def is_viewing(user_id, conversation_id) -> bool:
    return cache.get(_viewing_key(user_id)) == str(conversation_id)
