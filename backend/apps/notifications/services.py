"""The notification hub. Every module calls `notify`; nobody sends e-mails or SMS directly.

notify(user, "booking.confirmed", {"pro": "Aïcha", "date": "samedi 10 h"})
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.template import engines
from django.utils import timezone, translation

from apps.core.audit.services import json_safe
from apps.core.providers import ProviderError, ProviderNotConfigured

from . import quiet_hours, realtime
from .channels import SENDERS
from .models import Channel, Notification, NotificationDelivery, NotificationTemplate

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


def notify(user, event_key: str, context: dict | None = None, *, link: str | None = None):
    """Creates the notification and schedules every channel the person accepts.

    Texts come from the active templates of the event, in the language of the person.
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
    with translation.override(user.preferred_language):
        rendered = {
            channel: (
                _render(t.title, context),
                _render(t.body, context),
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
        delivery.save(update_fields=["status", "error", "updated_at"])
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
    delivery.save()
    return delivery.status


def mark_failed(delivery_id: str) -> None:
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
