"""The agenda WebSocket: an open agenda hears that something changed."""

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.booking.services import appointments
from apps.messaging.tests.factories import adult
from apps.pros.models import Trade

from .factories import at, salon, service


def _socket(token=None):
    from config.asgi import application

    headers = [(b"origin", b"http://testserver")]
    if token:
        headers.append((b"cookie", f"sg_access={token}".encode()))
    return WebsocketCommunicator(application, "/ws/agenda/", headers=headers)


@pytest.mark.django_db(transaction=True)
def test_visitors_and_people_without_agenda_are_refused():
    stranger = str(RefreshToken.for_user(adult("Awa")).access_token)

    async def scenario():
        results = []
        for token in (None, stranger):
            communicator = _socket(token)
            connected, _ = await communicator.connect()
            results.append(connected)
            await communicator.disconnect()
        return results

    assert async_to_sync(scenario)() == [False, False]


@pytest.mark.django_db(transaction=True)
def test_a_new_booking_refreshes_the_open_agenda():
    # Reference data is flushed between transactional tests.
    Trade.objects.get_or_create(key="braids", defaults={"name": "Tresses", "icon": "braids"})
    pro = salon()
    svc = service(pro, ("work", 60))
    token = str(RefreshToken.for_user(pro.user).access_token)
    client = adult("Awa")

    async def scenario():
        communicator = _socket(token)
        connected, _ = await communicator.connect()
        assert connected
        assert (await communicator.receive_json_from(timeout=3))["type"] == "hello"
        await database_sync_to_async(appointments.book)(pro, svc.pk, at(10), user=client)
        event = await communicator.receive_json_from(timeout=3)
        await communicator.send_json_to({"type": "ping"})
        pong = await communicator.receive_json_from(timeout=3)
        await communicator.disconnect()
        return event, pong

    event, pong = async_to_sync(scenario)()
    assert event == {"type": "agenda.changed"} and pong == {"type": "pong"}
