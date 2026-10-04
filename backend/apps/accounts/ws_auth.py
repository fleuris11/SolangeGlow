"""WebSocket sign-in: the same httpOnly access cookie as the API."""

from __future__ import annotations

from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .authentication import token_is_revoked


@database_sync_to_async
def _user_for(raw_token: str):
    from .models import User

    try:
        token = AccessToken(raw_token)
        user = User.objects.select_related("country").get(pk=token["user_id"])
    except (TokenError, KeyError, User.DoesNotExist):
        return AnonymousUser()
    if not user.is_active or token_is_revoked(user, token.get("iat")):
        return AnonymousUser()
    return user


class JwtCookieAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        cookies = SimpleCookie()
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                cookies.load(value.decode("latin-1"))
        morsel = cookies.get(settings.AUTH_COOKIES["ACCESS_NAME"])
        scope["user"] = await _user_for(morsel.value) if morsel else AnonymousUser()
        return await self.inner(scope, receive, send)
