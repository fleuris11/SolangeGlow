"""Errors sent to GlitchTip (Sentry protocol). Off without SENTRY_DSN; no personal data:
no user e-mail, IP or request body, and numbers and e-mails are masked in messages."""

from __future__ import annotations

from apps.core.logging import redact


def _scrub(event, hint):
    for exception in (event.get("exception") or {}).get("values") or []:
        if exception.get("value"):
            exception["value"] = redact(exception["value"])
    message = event.get("logentry") or {}
    if message.get("message"):
        message["message"] = redact(message["message"])
    request = event.get("request") or {}
    request.pop("data", None)
    request.pop("cookies", None)
    event.pop("user", None)
    return event


def init(dsn: str, *, environment: str, traces: float) -> None:
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        traces_sample_rate=traces,
        before_send=_scrub,
    )
