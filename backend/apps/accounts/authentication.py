"""JWT authentication for the API: Bearer header (future mobile app) or httpOnly cookies (web)."""

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def token_is_revoked(user, issued_at: int | None) -> bool:
    """True when the token was issued before "sign out on every device"."""
    revoked_at = getattr(user, "tokens_revoked_at", None)
    if revoked_at is None or issued_at is None:
        return False
    return int(issued_at) < int(revoked_at.timestamp())


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        from_cookie = header is None
        if from_cookie:
            raw_token = request.COOKIES.get(settings.AUTH_COOKIES["ACCESS_NAME"])
        else:
            raw_token = self.get_raw_token(header)
        if not raw_token:
            return None

        validated = self.get_validated_token(raw_token)
        user = self.get_user(validated)

        # Cookies travel by themselves; this header cannot be added by another site.
        needs_header = from_cookie and request.method not in SAFE_METHODS
        if needs_header and not request.headers.get(settings.AUTH_CLIENT_HEADER):
            raise exceptions.PermissionDenied(_("Request refused. Reload the page and try again."))

        if token_is_revoked(user, validated.get("iat")):
            raise exceptions.AuthenticationFailed(
                _("You were signed out. Sign in again."), code="token_revoked"
            )
        return user, validated
