"""Two-factor sign-in required for every team account in the admin (ADR-017)."""

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode

from .services import twofactor

OPEN = ("/admin/2fa/", "/admin/login/", "/admin/logout/", "/admin/jsi18n/")


class StaffTwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            settings.BACKOFFICE_REQUIRE_2FA
            and request.path.startswith("/admin/")
            and not request.path.startswith(OPEN)
            and user is not None
            and user.is_authenticated
            and user.is_staff
            and not twofactor.is_verified(request)
        ):
            return HttpResponseRedirect(
                f"{reverse('admin:backoffice_2fa')}?{urlencode({'next': request.get_full_path()})}"
            )
        return self.get_response(request)
