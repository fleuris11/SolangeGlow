from rest_framework.throttling import ScopedRateThrottle

from apps.core.selectors import get_setting

DEFAULT_RATES = {
    "auth": "30/minute",
    "otp_request": "10/minute",
    "guest": "10/hour",
    "profile": "60/minute",
    "media_upload": "30/hour",
    "notification_test": "10/hour",
}


class SettingRateThrottle(ScopedRateThrottle):
    """Per-IP rate limit whose value is a platform setting ("throttle.<scope>")."""

    def get_rate(self):
        return str(get_setting(f"throttle.{self.scope}", default=DEFAULT_RATES.get(self.scope)))
