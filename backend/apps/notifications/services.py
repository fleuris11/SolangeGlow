"""The notification hub. Every module calls `notify`; nobody sends e-mails or SMS directly.

notify(user, "booking.confirmed", {"pro": "Aïcha", "date": "samedi 10 h"})
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.template import engines
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.audit.services import json_safe
from apps.core.providers import ProviderError, ProviderNotConfigured

from . import quiet_hours, realtime
from .channels import SENDERS
from .models import (
    Channel,
    ContactMessage,
    Notification,
    NotificationDelivery,
    NotificationTemplate,
)

logger = logging.getLogger("solangeglow.notifications")

# Channels held back during quiet hours (they ring or vibrate).
NOISY = {Channel.PUSH, Channel.WHATSAPP, Channel.SMS}


def _render(text: str, context: dict, *, escape: bool = False) -> str:
    if not text:
        return ""
    source = text if escape else "{% autoescape off %}" + text + "{% endautoescape %}"
    template = engines["django"].from_string(source)
    return template.render(context).strip()


def wants(user, channel: str) -> bool:
    """The person accepts this channel (preferences and contact details)."""
    if channel == Channel.IN_APP:
        return True
    if channel == Channel.EMAIL:
        return user.notify_email and bool(user.email)
    if channel == Channel.PUSH:
        return user.notify_push and user.push_subscriptions.exists()
    if channel in (Channel.WHATSAPP, Channel.SMS):
        return user.notify_whatsapp and bool(user.phone)
    return False


def notification_payload(notification: Notification) -> dict:
    return {
        "id": str(notification.pk),
        "event_key": notification.event_key,
        "title": notification.title,
        "body": notification.body,
        "link": notification.link or None,
        "read": notification.read_at is not None,
        "created_at": notification.created_at.isoformat(),
    }


def unread_count(user) -> int:
    return Notification.objects.filter(user=user, in_app=True, read_at__isnull=True).count()


def notify(
    user,
    event_key: str,
    context: dict | None = None,
    *,
    link: str | None = None,
    secret: dict | None = None,
):
    """Creates the notification and schedules every channel the person accepts.

    Texts come from the active templates of the event, in the language of the person.
    `secret` values (a receipt code…) only go into the outside messages (SMS, WhatsApp,
    e-mail, push): never into the stored notification, and their text is hidden once sent.
    Returns the Notification, or None when the event has no active template.
    """
    if not user.is_active or user.deleted_at:
        return None
    templates = {
        t.channel: t
        for t in NotificationTemplate.objects.filter(event_key=event_key, is_active=True)
    }
    if not templates:
        logger.warning("No active template for event %s", event_key)
        return None

    context = {"first_name": user.first_name, **(context or {})}
    now = timezone.now()
    outside = {**context, **(secret or {})}
    with translation.override(user.preferred_language):
        rendered = {
            channel: (
                _render(t.title, context if channel == Channel.IN_APP else outside),
                _render(t.body, context if channel == Channel.IN_APP else outside),
                t.link,
            )
            for channel, t in templates.items()
        }

    in_app = rendered.get(Channel.IN_APP)
    first = in_app or next(iter(rendered.values()))
    with transaction.atomic():
        notification = Notification.objects.create(
            user=user,
            event_key=event_key,
            title=first[0],
            body=first[1],
            link=link or first[2],
            in_app=in_app is not None and wants(user, Channel.IN_APP),
            data=json_safe(context),
        )
        deliveries = []
        for channel, (title, body, _link) in rendered.items():
            if channel == Channel.IN_APP or not wants(user, channel):
                continue
            when = quiet_hours.next_allowed(user, now) if channel in NOISY else now
            deliveries.append(
                NotificationDelivery.objects.create(
                    notification=notification,
                    channel=channel,
                    title=title,
                    body=body,
                    scheduled_for=when,
                    sensitive=bool(secret),
                )
            )

    def after_commit():
        from .tasks import deliver_notification

        for delivery in deliveries:
            deliver_notification.apply_async(args=[str(delivery.pk)], eta=delivery.scheduled_for)
        if notification.in_app:
            realtime.push_update(user.pk, unread_count(user), notification_payload(notification))

    transaction.on_commit(after_commit)
    return notification


class RetryLater(Exception):
    """The channel failed for now: the task tries again."""


def deliver(delivery_id: str) -> str:
    """Sends one delivery. Idempotent: a sent or skipped delivery is not sent again."""
    delivery = (
        NotificationDelivery.objects.select_related("notification__user")
        .filter(pk=delivery_id)
        .first()
    )
    if delivery is None or delivery.status in (
        NotificationDelivery.Status.SENT,
        NotificationDelivery.Status.SKIPPED,
    ):
        return delivery.status if delivery else "missing"

    user = delivery.notification.user
    if not wants(user, delivery.channel):
        delivery.status = NotificationDelivery.Status.SKIPPED
        delivery.error = "preference"
        _hide_secret(delivery)
        delivery.save(update_fields=["status", "error", "body", "updated_at"])
        return delivery.status

    delivery.attempts += 1
    try:
        SENDERS[delivery.channel](delivery)
    except ProviderNotConfigured as exc:
        delivery.status = NotificationDelivery.Status.SKIPPED
        delivery.error = str(exc)[:255]
    except ProviderError as exc:
        delivery.error = str(exc)[:255]
        delivery.save(update_fields=["attempts", "error", "updated_at"])
        raise RetryLater(str(exc)) from exc
    else:
        delivery.status = NotificationDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.error = ""
    _hide_secret(delivery)
    delivery.save()
    return delivery.status


def _hide_secret(delivery: NotificationDelivery) -> None:
    if delivery.sensitive:
        delivery.body = gettext("(hidden once sent)")


def mark_failed(delivery_id: str) -> None:
    NotificationDelivery.objects.filter(pk=delivery_id, sensitive=True).update(
        body=gettext("(hidden once sent)")
    )
    NotificationDelivery.objects.filter(pk=delivery_id).update(
        status=NotificationDelivery.Status.FAILED, updated_at=timezone.now()
    )


def mark_read(user, ids: list[str] | None = None) -> int:
    queryset = Notification.objects.filter(user=user, read_at__isnull=True)
    if ids is not None:
        queryset = queryset.filter(pk__in=ids)
    count = queryset.update(read_at=timezone.now())
    realtime.push_update(user.pk, unread_count(user))
    return count


# --- Guests (no account): WhatsApp, then SMS -----------------------------------------------------

CONTACT_CHANNELS = (Channel.WHATSAPP, Channel.SMS)


def notify_contact(
    phone: str, event_key: str, context: dict | None = None, *, language: str = "fr"
):
    """Sends an event to a phone number without account (guest), in her language.

    WhatsApp when its template is active, else SMS; a WhatsApp that cannot be delivered
    falls back on SMS. Returns the ContactMessage, or None (no number, no template).
    """
    if not phone:
        return None
    templates = {
        t.channel: t
        for t in NotificationTemplate.objects.filter(
            event_key=event_key, channel__in=CONTACT_CHANNELS, is_active=True
        )
    }
    channel = next((c for c in CONTACT_CHANNELS if c in templates), None)
    if channel is None:
        logger.warning("No guest template for event %s", event_key)
        return None
    with translation.override(language):
        template = templates[channel]
        title = _render(template.title, context or {})
        body = _render(template.body, context or {})
    message = ContactMessage.objects.create(
        phone=phone, event_key=event_key, channel=channel, title=title, body=body
    )

    def after_commit():
        from .tasks import deliver_contact_message

        deliver_contact_message.delay(str(message.pk))

    transaction.on_commit(after_commit)
    return message


def deliver_contact(message_id: str) -> str:
    """Sends one guest message; WhatsApp that fails becomes an SMS (same text)."""
    from apps.core.providers import sms_client, whatsapp_client

    message = ContactMessage.objects.filter(pk=message_id).first()
    if message is None or message.status != ContactMessage.Status.PENDING:
        return message.status if message else "missing"
    message.attempts += 1
    try:
        if message.channel == Channel.WHATSAPP:
            text = "\n".join(filter(None, (message.title, message.body)))
            whatsapp_client().send_text(message.phone, text)
        else:
            sms_client().send(message.phone, message.body)
    except (ProviderNotConfigured, ProviderError) as exc:
        message.error = str(exc)[:255]
        if message.channel == Channel.WHATSAPP:
            message.channel = Channel.SMS
            message.save(update_fields=["channel", "error", "attempts", "updated_at"])
            return deliver_contact(message_id)
        message.status = ContactMessage.Status.FAILED
    else:
        message.status = ContactMessage.Status.SENT
        message.sent_at = timezone.now()
    message.save()
    return message.status


def send_direct(
    channel: str, destination: str, subject: str, body: str, *, unsubscribe_url: str = ""
):
    """A message to someone who may have no account (campaigns, gift cards): e-mail or
    WhatsApp, sent now. Returns "" when sent, else the reason it was not."""
    from django.core.mail import EmailMessage

    from apps.core.providers import whatsapp_client

    if not destination:
        return "no_destination"
    try:
        if channel == Channel.EMAIL:
            headers = {}
            if unsubscribe_url:
                headers["List-Unsubscribe"] = f"<{unsubscribe_url}>"
                body = f"{body}\n\n{unsubscribe_url}"
            EmailMessage(
                subject, body, settings.DEFAULT_FROM_EMAIL, [destination], headers=headers
            ).send()
        else:
            text = "\n".join(filter(None, (subject, body, unsubscribe_url)))
            whatsapp_client(allow_console=settings.DEBUG).send_text(destination, text)
    except (ProviderNotConfigured, ProviderError) as exc:
        return str(exc)[:200] or exc.__class__.__name__
    except Exception as exc:
        logger.warning("Direct message not sent: %s", exc.__class__.__name__)
        return exc.__class__.__name__
    return ""
