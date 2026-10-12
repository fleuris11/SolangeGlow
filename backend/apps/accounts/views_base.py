"""Base views shared by modules."""

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .authentication import CookieJWTAuthentication, OptionalCookieJWTAuthentication
from .throttling import SettingRateThrottle


class OptionalAuthView(APIView):
    """Open to everyone; a signed-in visitor is recognised (an expired session is ignored)."""

    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "search"

    def get_authenticators(self):
        if getattr(self, "swagger_fake_view", False):  # one sign-in scheme in the schema
            return [CookieJWTAuthentication()]
        return [OptionalCookieJWTAuthentication()]
