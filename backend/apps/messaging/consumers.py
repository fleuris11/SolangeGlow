"""One WebSocket per device for the messaging: live messages, receipts, typing, presence.

Messages are sent through the API (reliable, idempotent); the socket carries the rest.
From the device: ping (every 30 s), viewing (the open conversation or null), typing,
read, delivered. To the device: every event of `realtime.send_to`.
"""

from __future__ import annotations

import contextlib
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import errors, realtime, selectors, services


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class MessagingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user = user
        self.group = realtime.group_name(user.pk)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        devices = await database_sync_to_async(realtime.device_connected)(user.pk)
        await database_sync_to_async(realtime.mark_online)(user.pk)
        if devices == 1:
            await database_sync_to_async(services.presence_changed)(user, True)
        await self.send_json(
            {
                "type": "hello",
                "count": await database_sync_to_async(selectors.unread_conversation_count)(user),
                "requests": await database_sync_to_async(selectors.request_count)(user),
            }
        )

    async def disconnect(self, code):
        if not hasattr(self, "group"):
            return
        await self.channel_layer.group_discard(self.group, self.channel_name)
        if await database_sync_to_async(realtime.device_disconnected)(self.user.pk) == 0:
            await database_sync_to_async(realtime.mark_offline)(self.user.pk)
            await database_sync_to_async(services.presence_changed)(self.user, False)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type") if isinstance(content, dict) else None
        conversation = _uuid(content.get("conversation")) if isinstance(content, dict) else None
        if kind == "ping":
            await database_sync_to_async(realtime.mark_online)(self.user.pk)
            await self.send_json({"type": "pong"})
        elif kind == "viewing":
            allowed = conversation and await database_sync_to_async(selectors.is_member)(
                self.user, conversation
            )
            await database_sync_to_async(realtime.set_viewing)(
                self.user.pk, conversation if allowed else None
            )
        elif kind == "typing" and conversation:
            await database_sync_to_async(services.typing)(self.user, conversation)
        elif kind == "read" and conversation:
            with contextlib.suppress(errors.ConversationNotFound):
                await database_sync_to_async(services.mark_read)(self.user, conversation)
        elif kind == "delivered":
            await database_sync_to_async(services.mark_delivered)(self.user)

    async def relay(self, event):
        await self.send_json(event["event"])
