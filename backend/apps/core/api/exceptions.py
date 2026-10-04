"""Uniform API error format: {"code": "...", "message": "...", "fields": {...}}."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.errors import DomainError


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        response = Response(
            {"code": exc.code, "message": str(exc.message), "fields": {}, **exc.details},
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
        return None

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
        "message": str(detail) if detail is not None else str(exc),
        "fields": {},
    }
    return response
