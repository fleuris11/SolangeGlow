"""Versions of the contents: a copy of every field (all languages) at each save, read or
brought back from the admin. Works for pages, banners, the FAQ and the message templates."""

from __future__ import annotations

import datetime
import decimal
import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Max

from apps.core.audit.services import record

from ..models import ContentVersion

SKIPPED = {"id", "created_at", "updated_at", "version"}


def _plain(value):
    if isinstance(value, datetime.datetime | datetime.date):
        return value.isoformat()
    if isinstance(value, uuid.UUID | decimal.Decimal):
        return str(value)
    return value


def _fields(obj):
    return [f for f in obj._meta.concrete_fields if f.name not in SKIPPED]


def snapshot(obj, *, author=None) -> ContentVersion:
    """A new version of the content as it is now."""
    content_type = ContentType.objects.get_for_model(obj)
    with transaction.atomic():
        last = (
            ContentVersion.objects.select_for_update()
            .filter(content_type=content_type, object_id=str(obj.pk))
            .aggregate(n=Max("number"))["n"]
            or 0
        )
        found = ContentVersion.objects.create(
            content_type=content_type,
            object_id=str(obj.pk),
            number=last + 1,
            data={f.attname: _plain(getattr(obj, f.attname)) for f in _fields(obj)},
            author=author,
        )
        if hasattr(obj, "version"):
            type(obj).objects.filter(pk=obj.pk).update(version=found.number)
            obj.version = found.number
    return found


def history(obj):
    return ContentVersion.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=str(obj.pk)
    ).select_related("author")


@transaction.atomic
def restore(version: ContentVersion, *, actor):
    """Brings the content back as it was in this version (a new version is written)."""
    obj = version.content_type.get_object_for_this_type(pk=version.object_id)
    names = {f.attname for f in _fields(obj)}
    for attname, value in version.data.items():
        if attname in names:
            setattr(obj, attname, value)
    obj.save()
    found = snapshot(obj, author=actor)
    record(
        "content.version_restored",
        obj,
        actor=actor,
        metadata={"from": version.number, "to": found.number},
    )
    return obj
