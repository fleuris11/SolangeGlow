"""In the back-office, an expected refusal (file too large, rule not met...) is said in a message
on the screen the person was on, never with an error page."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect

from apps.core.errors import DomainError


class AdminDomainErrorMiddleware:
    """After MessageMiddleware. The admin runs a save in a transaction: nothing is half-saved."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not request.path.startswith("/admin/") or not isinstance(exception, DomainError):
            return None
        messages.error(request, exception.text())
        return redirect(request.get_full_path())
