"""One WebSocket per open agenda: « something changed », the agenda reloads its days.

The socket only carries the signal; the agenda is read again through the API (the
collaborator only sees what she may see).
"""

from __future__ import annotations

import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import selectors
from .services.common import agenda_group


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class AgendaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        query = dict(
            pair.split("=", 1)
            for pair in self.scope.get("query_string", b"").decode().split("&")
            if "=" in pair
        )
        pro, _ = await database_sync_to_async(selectors.agenda_access)(
            user, _uuid(query.get("pro"))
        )
        if pro is None:
            await self.close(code=4404)
            return
        self.group = agenda_group(pro.pk)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "hello"})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def relay(self, event):
        await self.send_json(event["event"])
