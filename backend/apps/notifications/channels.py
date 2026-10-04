"""Outside channels of the hub. Each `send` raises ProviderNotConfigured or ProviderError."""

from __future__ import annotations

import json
import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from pywebpush import WebPushException, webpush

from apps.core.providers import ProviderError, ProviderNotConfigured, sms_client, whatsapp_client

from . import vapid
from .models import NotificationDelivery, PushSubscription

logger = logging.getLogger("solangeglow.notifications")


def send_email(delivery: NotificationDelivery) -> None:
    user = delivery.notification.user
    if not user.email:
        raise ProviderNotConfigured("no e-mail address")
    link = delivery.notification.link
    body = delivery.body
    if link:
        body = f"{body}\n\n{settings.SITE_URL.rstrip('/')}/{user.preferred_language}{link}"
    try:
        send_mail(delivery.title, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except (SMTPException, OSError) as exc:
        raise ProviderError("e-mail failed") from exc


def send_push(delivery: NotificationDelivery) -> None:
    user = delivery.notification.user
    subscriptions = list(PushSubscription.objects.filter(user=user))
    if not subscriptions:
        raise ProviderNotConfigured("no device subscribed")
    payload = json.dumps(
        {
            "title": delivery.title,
            "body": delivery.body,
            "url": f"/{user.preferred_language}{delivery.notification.link or '/notifications'}",
            "tag": str(delivery.notification_id),
        }
    )
    signer = vapid.signer()
    delivered = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=signer,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):  # the browser dropped this subscription
                subscription.delete()
                continue
            logger.warning("Push failed (HTTP %s)", status)
            continue
        subscription.last_used_at = timezone.now()
        subscription.save(update_fields=["last_used_at", "updated_at"])
        delivered += 1
    if not delivered:
        if not PushSubscription.objects.filter(user=user).exists():
            raise ProviderNotConfigured("every device unsubscribed")
        raise ProviderError("no push delivered")


def send_whatsapp(delivery: NotificationDelivery) -> None:
    user = delivery.notification.user
    if not user.phone:
        raise ProviderNotConfigured("no phone number")
    # Outside the 24-hour window Meta only accepts approved templates: the free text below
    # works for replies; event templates are created in Meta Business when WhatsApp opens.
    whatsapp_client().send_text(str(user.phone), f"{delivery.title}\n{delivery.body}".strip())


def send_sms(delivery: NotificationDelivery) -> None:
    user = delivery.notification.user
    if not user.phone:
        raise ProviderNotConfigured("no phone number")
    sms_client().send(str(user.phone), delivery.body)


SENDERS = {
    "email": send_email,
    "push": send_push,
    "whatsapp": send_whatsapp,
    "sms": send_sms,
}
