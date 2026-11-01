"""« Download my data » (GDPR right of access): her account and every row that points to
it, one JSON file per kind, in a ZIP. Built on request, never stored."""

from __future__ import annotations

import datetime
import decimal
import io
import json
import uuid
import zipfile

from django.db import models
from django.utils import timezone

from apps.core.selectors import get_setting

from .models import User

# Secrets and internal records: never part of an export.
EXCLUDED_MODELS = {
    "accounts.OtpChallenge",
    "accounts.GuestIdentity",
    "backoffice.StaffDevice",
    "backoffice.RecoveryCode",
    "backoffice.Impersonation",
    "core.AuditEvent",
    "pros.ProVerification",
    "token_blacklist.OutstandingToken",
}
SECRET_WORDS = ("password", "hash", "secret", "token", "encrypted", "key")


def _value(value):
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, uuid.UUID | decimal.Decimal):
        return str(value)
    if isinstance(value, models.fields.files.FieldFile):
        return value.name or None
    return value


def _row(obj: models.Model) -> dict:
    data = {}
    for field in obj._meta.concrete_fields:
        if any(word in field.name for word in SECRET_WORDS):
            continue
        data[field.attname] = _value(getattr(obj, field.attname))
    return data


def _related(user: User, most: int):
    for relation in User._meta.related_objects:
        if not (relation.one_to_many or relation.one_to_one):
            continue
        model = relation.related_model
        if model._meta.label in EXCLUDED_MODELS:
            continue
        rows = model._default_manager.filter(**{relation.field.name: user}).order_by("pk")
        found = [_row(obj) for obj in rows[:most]]
        if found:
            yield f"{model._meta.label_lower}.{relation.field.name}", found


def build(user: User) -> bytes:
    most = int(get_setting("privacy.export_max_rows", default=5_000))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "account.json", json.dumps(_row(user), ensure_ascii=False, indent=2, default=str)
        )
        for name, rows in _related(user, most):
            archive.writestr(
                f"{name}.json", json.dumps(rows, ensure_ascii=False, indent=2, default=str)
            )
        archive.writestr(
            "README.txt",
            f"Solange Glow - export of {timezone.now():%Y-%m-%d %H:%M} UTC.\n"
            "One JSON file per kind of data linked to your account.\n",
        )
    return buffer.getvalue()
