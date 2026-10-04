import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# Initialise Django before importing anything that touches models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.accounts.ws_auth import JwtCookieAuthMiddleware  # noqa: E402
from apps.notifications.routing import websocket_urlpatterns as notification_routes  # noqa: E402

# Each module adds its WebSocket routes here (messaging will be next).
websocket_urlpatterns = [*notification_routes]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JwtCookieAuthMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
