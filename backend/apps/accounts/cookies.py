from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

GUEST_COOKIE = "sg_guest"
# Readable by the web app, holds no secret: only says "a session exists", so a visitor's
# browser does not call the API for nothing.
SESSION_HINT_COOKIE = "sg_signed_in"


def _common():
    config = settings.AUTH_COOKIES
    return {
        "secure": config["SECURE"],
        "samesite": config["SAMESITE"],
        "domain": config["DOMAIN"],
        "httponly": True,
    }


def set_auth_cookies(response, refresh: RefreshToken) -> None:
    config = settings.AUTH_COOKIES
    jwt = settings.SIMPLE_JWT
    response.set_cookie(
        config["ACCESS_NAME"],
        str(refresh.access_token),
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        **_common(),
    )
    response.set_cookie(
        config["REFRESH_NAME"],
        str(refresh),
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=config["REFRESH_PATH"],
        **_common(),
    )
    response.set_cookie(
        SESSION_HINT_COOKIE,
        "1",
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        **{**_common(), "httponly": False},
    )


def clear_auth_cookies(response) -> None:
    config = settings.AUTH_COOKIES
    response.delete_cookie(config["ACCESS_NAME"], path="/", domain=config["DOMAIN"])
    response.delete_cookie(
        config["REFRESH_NAME"], path=config["REFRESH_PATH"], domain=config["DOMAIN"]
    )
    response.delete_cookie(SESSION_HINT_COOKIE, path="/", domain=config["DOMAIN"])


def set_guest_cookie(response, guest_id: str) -> None:
    response.set_cookie(GUEST_COOKIE, guest_id, max_age=60 * 60 * 24 * 365, path="/", **_common())


def clear_guest_cookie(response) -> None:
    response.delete_cookie(GUEST_COOKIE, path="/", domain=settings.AUTH_COOKIES["DOMAIN"])
