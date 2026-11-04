"""Uniform API error format: {"code": "...", "message": "...", "fields": {...}}.

The message is shown as it is to the person: never a technical word.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from apps.core.errors import DomainError

logger = logging.getLogger(__name__)


def _clear_message(exc) -> str:
    if isinstance(exc, exceptions.NotAuthenticated):
        return _("Sign in to continue.")
    if isinstance(exc, exceptions.AuthenticationFailed):
        return _("You have been signed out. Sign in again to continue.")
    if isinstance(exc, exceptions.PermissionDenied):
        return _("Your account cannot do this.")
    if isinstance(exc, exceptions.NotFound):
        return _("We could not find what you are looking for.")
    if isinstance(exc, exceptions.Throttled):
        return _("Too many tries. Wait a moment, then try again.")
    if isinstance(exc, exceptions.MethodNotAllowed):
        return _("This action is not possible here.")
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return _("This type of file is not accepted.")
    if isinstance(exc, exceptions.ParseError):
        return _("We could not read what was sent. Try again.")
    return _("Something went wrong on our side. Try again in a moment.")


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        response = Response(
            {"code": exc.code, "message": exc.text(), "fields": {}, **exc.details},
            status=exc.status_code,
        )
        retry_after = exc.details.get("retry_after")
        if retry_after:
            response["Retry-After"] = str(retry_after)
        return response

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        # A bug: logged (and sent to the error tracker), never shown.
        logger.exception("Unexpected error in the API", exc_info=exc)
        set_rollback()
        return Response(
            {"code": "server_error", "message": _clear_message(exc), "fields": {}}, status=500
        )

    if isinstance(exc, exceptions.ValidationError):
        detail = exc.detail
        fields = detail if isinstance(detail, dict) else {"non_field_errors": detail}
        response.data = {
            "code": "validation_error",
            "message": _("Some information is missing or incorrect."),
            "fields": fields,
        }
        return response

    detail = getattr(exc, "detail", None)
    response.data = {
        "code": getattr(detail, "code", None) or getattr(exc, "default_code", "error"),
        "message": _clear_message(exc),
        "fields": {},
    }
    return response
