import hmac
import ipaddress

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from apps.core.selectors import get_setting

DEFAULT_RATES = {
    "auth": "30/minute",
    "otp_request": "10/minute",
    "guest": "10/hour",
    "profile": "60/minute",
    "media_upload": "30/hour",
    "notification_test": "10/hour",
    "search": "120/minute",
    "printable": "30/minute",
    "arrival": "20/hour",
    "verification": "5/hour",
    "social_write": "120/hour",
    "report": "30/hour",
    "message_send": "120/minute",
    "payments": "60/minute",
    "receipt_code": "20/hour",
    "shop": "120/minute",
    "selection": "60/minute",
    "booking": "60/minute",
    "salon": "120/minute",
    "widget": "120/minute",
    "academy": "240/minute",
    "live": "240/minute",
    "live_write": "20/minute",
    "calls": "60/minute",
    "gifts": "60/minute",
    "gift_code": "20/hour",
    "games": "120/minute",
    "ads": "240/minute",
    "content": "240/minute",
    "help_ticket": "10/hour",
    "data_export": "5/hour",
}


def forwarded_ip(request) -> str | None:
    """The visitor's address sent by the app's own server (pages rendered by Next all come
    from one address). Trusted only with the shared secret INTERNAL_API_TOKEN."""
    token = settings.INTERNAL_API_TOKEN
    given = request.META.get("HTTP_X_SG_INTERNAL", "")
    if not token or not given or not hmac.compare_digest(given, token):
        return None
    address = request.META.get("HTTP_X_SG_CLIENT_IP", "").strip()
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return None


class ClientIdentMixin:
    def get_ident(self, request):
        return forwarded_ip(request) or super().get_ident(request)


class AnonThrottle(ClientIdentMixin, AnonRateThrottle):
    pass


class UserThrottle(ClientIdentMixin, UserRateThrottle):
    pass


class SettingRateThrottle(ClientIdentMixin, ScopedRateThrottle):
    """Per-IP rate limit whose value is a platform setting ("throttle.<scope>")."""

    def get_rate(self):
        return str(get_setting(f"throttle.{self.scope}", default=DEFAULT_RATES.get(self.scope)))
