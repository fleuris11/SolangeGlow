"""Shared steps of the booking services: references, who is told what, agenda refresh."""

from __future__ import annotations

import datetime
import secrets

import phonenumbers
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.utils import formats, timezone, translation

from apps.core.selectors import get_setting
from apps.notifications.services import notify, notify_contact
from apps.pros.hours import zone_of

from .. import availability
from ..models import Appointment, AppointmentStep, BookingSettings

A = Appointment.Status


# --- What other modules add (registered in their AppConfig.ready) -----------------------------

_completed_hooks: list = []
_deposit_covers: list = []


def on_completed(callback) -> None:
    """callback(appointment) after an appointment is done (packages, stock…)."""
    if callback not in _completed_hooks:
        _completed_hooks.append(callback)


def run_completed(appointment) -> None:
    """Each module after a done appointment; a refusal of one never blocks the others."""
    import logging

    from apps.core.errors import DomainError

    for callback in list(_completed_hooks):
        try:
            with transaction.atomic():
                callback(appointment)
        except DomainError as exc:
            logging.getLogger("solangeglow.booking").info("After completion: %s", exc.code)


def deposit_cover(callback) -> None:
    """callback(appointment, code, actor) -> bool: pays a deposit another way (gift card)."""
    if callback not in _deposit_covers:
        _deposit_covers.append(callback)


def cover_deposit(appointment, code: str, actor) -> bool:
    return any(callback(appointment, code, actor) for callback in list(_deposit_covers))


def new_reference() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "RDV-" + "".join(secrets.choice(alphabet) for _ in range(7))


def settings_of(pro) -> BookingSettings:
    return availability.settings_of(pro)


def setting(key: str, pro, default, own=None):
    if own is not None:
        return own
    return get_setting(key, country=pro.country, default=default)


def normalize_phone(raw: str) -> str:
    try:
        number = phonenumbers.parse(raw or "", settings.PHONENUMBER_DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        return ""
    if not phonenumbers.is_valid_number(number):
        return ""
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def guest_for(name: str, phone: str):
    """The guest of this number (not yet a client), her first name kept up to date."""
    from apps.accounts.models import GuestIdentity
    from apps.accounts.services import create_guest

    found = (
        GuestIdentity.objects.filter(phone=phone, user__isnull=True).order_by("-created_at").first()
    )
    if found is None:
        return create_guest(first_name=name, phone=phone)
    if found.first_name != name:
        found.first_name = name
        found.save(update_fields=["first_name", "updated_at"])
    return found


def agenda_group(pro_id) -> str:
    return f"agenda.{pro_id}"


def changed(pro) -> None:
    """The agenda moved: cached slots are obsolete, open agendas refresh (after commit)."""
    availability.bump(pro.pk)

    def push():
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(
                agenda_group(pro.pk), {"type": "relay", "event": {"type": "agenda.changed"}}
            )

    transaction.on_commit(push)


def when_text(appointment: Appointment, language: str = "fr") -> str:
    """« mardi 21 octobre à 10:30 » in the pro's time zone and the reader's language."""
    local = appointment.starts_at.astimezone(zone_of(appointment.pro))
    with translation.override(language):
        return formats.date_format(local, "l j F, H:i")


def manage_link(appointment: Appointment) -> str:
    return f"/rdv/{appointment.manage_token}"


def tell_client(appointment: Appointment, event: str, extra: dict | None = None) -> None:
    """The client (account) or the guest (WhatsApp, else SMS), after the commit."""
    client = appointment.client

    def send():
        language = getattr(client, "preferred_language", "") or "fr"
        context = {
            "pro": appointment.pro.display_name,
            "service": appointment.service.name,
            "when": when_text(appointment, language),
            "reference": appointment.reference,
            "link": f"{settings.SITE_URL.rstrip('/')}/{language}{manage_link(appointment)}",
            **(extra or {}),
        }
        if client is not None:
            notify(client, event, context, link=f"/appointments/{appointment.pk}")
        else:
            notify_contact(appointment.client_phone, event, context, language=language)

    transaction.on_commit(send)


def tell_pro(appointment: Appointment, event: str, extra: dict | None = None) -> None:
    """The pro, and the collaborators working on the appointment."""
    recipients = {appointment.pro.user}
    for step in appointment.steps.select_related("staff__user"):
        if step.staff is not None and step.staff.user is not None:
            recipients.add(step.staff.user)

    def send():
        for person in recipients:
            context = {
                "client": appointment.client_name,
                "service": appointment.service.name,
                "when": when_text(appointment, person.preferred_language or "fr"),
                "reference": appointment.reference,
                **(extra or {}),
            }
            notify(person, event, context, link=f"/pro/agenda?day={appointment.starts_at.date()}")

    transaction.on_commit(send)


def set_blocking(appointment: Appointment) -> None:
    AppointmentStep.objects.filter(appointment=appointment).update(
        blocking=appointment.status in Appointment.BLOCKING
    )


def write_steps(appointment: Appointment, slot) -> None:
    """Replaces the steps of an appointment by those of a computed slot."""
    AppointmentStep.objects.filter(appointment=appointment).delete()
    AppointmentStep.objects.bulk_create(
        AppointmentStep(
            appointment=appointment,
            position=position,
            kind=kind,
            label=label,
            starts_at=datetime.datetime.fromtimestamp(start, tz=datetime.UTC),
            ends_at=datetime.datetime.fromtimestamp(end, tz=datetime.UTC),
            staff_id=staff,
            resource_id=resource,
            blocking=appointment.status in Appointment.BLOCKING,
        )
        for position, kind, label, start, end, staff, resource in slot.steps
    )


def now() -> datetime.datetime:
    return timezone.now()
