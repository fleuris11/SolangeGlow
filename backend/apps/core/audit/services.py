"""Writing the audit journal. Sensitive values are masked before they are stored."""

from __future__ import annotations

import datetime
import decimal
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models

from . import context
from .models import AuditEvent

MASK = "***"
SENSITIVE_FIELDS = {
    "password",
    "code_hash",
    "destination",
    "destination_hash",
    "ip_hash",
    "token",
    "endpoint",
    "p256dh",
    "auth",
}


def _json_value(value):
    if isinstance(value, models.Model):
        return str(value.pk)
    if isinstance(value, (uuid.UUID, decimal.Decimal)):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "name") and hasattr(value, "storage"):  # file fields
        return value.name or None
    return str(value)


json_safe = _json_value


def snapshot(instance: models.Model | None) -> dict | None:
    """Concrete field values of an object, JSON-safe, sensitive fields masked."""
    if instance is None:
        return None
    data = {}
    for field in instance._meta.concrete_fields:
        value = getattr(instance, field.attname)
        if field.name in SENSITIVE_FIELDS and value:
            data[field.name] = MASK
        else:
            data[field.name] = _json_value(value)
    return data


def diff(before: dict | None, after: dict | None) -> tuple[dict | None, dict | None]:
    """Keep only the fields that changed (timestamps excluded)."""
    if not before or not after:
        return before, after

    def same(a, b):
        # An empty text and "nothing" are the same for a reader of the journal.
        return a == b or (a in (None, "") and b in (None, ""))

    keys = [k for k in after if k != "updated_at" and not same(before.get(k), after.get(k))]
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


def record(
    action: str,
    target: models.Model | None = None,
    *,
    actor=None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    """Add a line to the audit journal. Actor and IP default to the current request."""
    current = context.current()
    actor_id = actor.pk if actor is not None else current.actor_id
    return AuditEvent.objects.create(
        actor_id=actor_id,
        action=action,
        target_type=ContentType.objects.get_for_model(target) if target is not None else None,
        target_id=str(target.pk) if target is not None and target.pk is not None else "",
        target_repr=str(target)[:200] if target is not None else "",
        before=before,
        after=after,
        metadata=_json_value(metadata or {}),
        ip_address=current.ip,
        user_agent=current.user_agent,
    )
