"""Live updates of the unread counter through Channels (WebSocket)."""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("solangeglow.notifications")


def group_name(user_id) -> str:
    return f"notifications.{user_id}"


def push_update(user_id, unread: int, notification: dict | None = None) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            group_name(user_id),
            {"type": "notification.update", "unread": unread, "notification": notification},
        )
    except Exception:
        logger.warning("Real-time update failed", exc_info=True)
