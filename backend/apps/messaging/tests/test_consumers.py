"""The messaging WebSocket: live messages, typing, receipts, presence."""

import asyncio

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.messaging import realtime, services
from apps.messaging.models import ConversationMember
from apps.pros.models import Trade

from .factories import adult, pro


def _token(user) -> str:
    """Made before the async part: creating a token touches the database."""
    return str(RefreshToken.for_user(user).access_token)


def _socket(token):
    from config.asgi import application

    return WebsocketCommunicator(
        application,
        "/ws/messaging/",
        headers=[(b"cookie", f"sg_access={token}".encode()), (b"origin", b"http://testserver")],
    )


async def _next(communicator, kind, *, timeout=3):
    """The next event of this type (others, like presence, are skipped)."""
    while True:
        event = await communicator.receive_json_from(timeout=timeout)
        if event.get("type") == kind:
            return event


@pytest.mark.django_db(transaction=True)
def test_visitors_are_refused():
    from config.asgi import application

    async def scenario():
        communicator = WebsocketCommunicator(
            application, "/ws/messaging/", headers=[(b"origin", b"http://testserver")]
        )
        connected, _ = await communicator.connect()
        return connected

    assert async_to_sync(scenario)() is False


@pytest.fixture
def trades():
    """Real transactions (Channels runs in other threads) empty the tables between tests,
    including the trades written by a data migration: put back the one the pros use."""
    Trade.objects.get_or_create(key="braids", defaults={"name": "Tresses", "icon": "braids"})


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("trades")
def test_live_message_typing_and_read_receipt():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    her_token, my_token = _token(aicha), _token(awa)

    async def scenario():
        her_phone, my_phone = _socket(her_token), _socket(my_token)
        assert (await her_phone.connect())[0] and (await my_phone.connect())[0]
        hello = await _next(her_phone, "hello")
        assert hello == {"type": "hello", "count": 0, "requests": 0}
        await _next(my_phone, "hello")

        # The message is sent through the API; it arrives live on her phone.
        await database_sync_to_async(services.send)(awa, conversation.pk, text="Bonjour")
        event = await _next(her_phone, "message")
        assert event["message"]["text"] == "Bonjour"
        unread = await _next(her_phone, "unread")
        assert unread["count"] == 1

        await my_phone.send_json_to({"type": "typing", "conversation": str(conversation.pk)})
        typing = await _next(her_phone, "typing")
        assert typing == {
            "type": "typing",
            "conversation": str(conversation.pk),
            "user": str(awa.pk),
        }

        await her_phone.send_json_to({"type": "read", "conversation": str(conversation.pk)})
        receipt = await _next(my_phone, "receipt")
        assert receipt["user"] == str(aicha.pk) and receipt["read_up_to"]

        await her_phone.send_json_to({"type": "ping"})
        assert await _next(her_phone, "pong") == {"type": "pong"}
        await her_phone.disconnect()
        offline = await _next(my_phone, "presence")
        await my_phone.disconnect()
        return offline

    offline = async_to_sync(scenario)()
    assert offline["user"] == str(aicha.pk) and offline["online"] is False
    member = ConversationMember.objects.get(conversation=conversation, user=aicha)
    assert member.read_up_to is not None


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("trades")
def test_viewing_a_conversation_and_presence():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    services.send(awa, conversation.pk, text="Bonjour")
    other = services.start_direct(adult("Zoé"), pro("Gloria Nails"))
    token = _token(aicha)

    async def scenario():
        phone = _socket(token)
        await phone.connect()
        await _next(phone, "hello")
        await phone.send_json_to({"type": "viewing", "conversation": str(conversation.pk)})
        await phone.send_json_to({"type": "ping"})
        await _next(phone, "pong")
        state = (
            await database_sync_to_async(realtime.is_online)(aicha.pk),
            await database_sync_to_async(realtime.is_viewing)(aicha.pk, conversation.pk),
        )
        # Someone else's conversation cannot be "viewed".
        await phone.send_json_to({"type": "viewing", "conversation": str(other.pk)})
        await phone.send_json_to({"type": "ping"})
        await _next(phone, "pong")
        viewing_other = await database_sync_to_async(realtime.is_viewing)(aicha.pk, other.pk)
        await phone.disconnect()
        await asyncio.sleep(0)
        return state, viewing_other

    (online, viewing), viewing_other = async_to_sync(scenario)()
    assert online and viewing and not viewing_other
    assert realtime.is_online(aicha.pk) is False
    assert realtime.last_seen(aicha.pk)
