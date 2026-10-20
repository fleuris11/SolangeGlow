from django.urls import path

from .consumers import AgendaConsumer

websocket_urlpatterns = [
    path("ws/agenda/", AgendaConsumer.as_asgi()),
]
