"""Who is acting and from where, for the duration of a request (or a task)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditContext:
    actor_id: object | None = None
    ip: str | None = None
    user_agent: str = ""


_EMPTY = AuditContext()
_current: ContextVar[AuditContext | None] = ContextVar("audit_context", default=None)


def current() -> AuditContext:
    return _current.get() or _EMPTY


def set_current(context: AuditContext):
    return _current.set(context)


def reset(token) -> None:
    _current.reset(token)


class AuditContextMiddleware:
    """Remembers the signed-in person and the IP so services can audit without plumbing.

    DRF authenticates later than Django middleware: API views set the actor themselves
    through `audit.record(actor=...)` when it matters.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = set_current(
            AuditContext(
                actor_id=user.pk if user is not None and user.is_authenticated else None,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
            )
        )
        try:
            return self.get_response(request)
        finally:
            reset(token)
