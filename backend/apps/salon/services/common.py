"""Shared steps of the salon services."""

from __future__ import annotations

from apps.booking.models import ClientRecord
from apps.core.selectors import get_setting

from .. import errors


def setting(key: str, pro, default):
    return get_setting(key, country=pro.country, default=default)


def record_of(pro, record_id) -> ClientRecord:
    found = ClientRecord.objects.select_related("client").filter(pk=record_id, pro=pro).first()
    if found is None:
        raise errors.NotFound()
    return found


def destination(record: ClientRecord, channel: str) -> str:
    """Where a message to this client goes (her file first, then her account)."""
    client = record.client
    if channel == "email":
        return record.email or (client.email if client is not None and client.email else "")
    phone = record.phone or (str(client.phone) if client is not None and client.phone else "")
    return str(phone or "")


def birthday(record: ClientRecord):
    """(day, month) of her birthday, from her file or from her account."""
    if record.birthday_day and record.birthday_month:
        return record.birthday_day, record.birthday_month
    client = record.client
    if client is not None and client.birth_date:
        return client.birth_date.day, client.birth_date.month
    return None


def first_name(record: ClientRecord) -> str:
    client = record.client
    if client is not None and client.first_name:
        return client.first_name
    return (record.name or "").split(" ")[0]
