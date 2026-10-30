"""The help center: tickets sent from « Contact us », answered from the admin."""

from __future__ import annotations

import logging
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.core.audit.services import record
from apps.core.providers import ProviderError, ProviderNotConfigured
from apps.notifications.services import notify, send_direct

from .. import errors
from ..assistant import assistant
from ..models import Ticket

logger = logging.getLogger("solangeglow.content")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def suggestions(question: str, language: str) -> dict:
    """What the assistant proposes before the ticket: answers of the FAQ (and later an AI)."""
    helper = assistant()
    answer = None
    try:
        answer = helper.answer(question, language)
    except (ProviderError, ProviderNotConfigured) as exc:
        logger.info("Help assistant unavailable: %s", exc)
    return {"answer": answer, "faq": helper.suggest(question, language)}


def create_ticket(*, user, name: str, email: str, phone: str, topic: str, message: str, language):
    name = (name or (user.first_name if user else "") or "").strip()[:120]
    email = (email or (user.email if user else "") or "").strip()
    phone = (phone or (str(user.phone) if user and user.phone else "") or "").strip()[:30]
    if not name or not (email or phone or user):
        raise errors.ContactNeeded()
    while True:
        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    reference="T-" + "".join(secrets.choice(ALPHABET) for _n in range(6)),
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    topic=topic or "",
                    message=message.strip()[:3000],
                    language=language or "fr",
                )
            break
        except IntegrityError:
            continue
    record("content.ticket_created", ticket, actor=user)
    return ticket


@transaction.atomic
def answer(ticket: Ticket, text: str, *, actor) -> Ticket:
    """The answer goes to her account (notification) or to her e-mail address."""
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    ticket.answer = text.strip()
    ticket.status = Ticket.Status.ANSWERED
    ticket.answered_at = timezone.now()
    ticket.answered_by = actor
    ticket.save(update_fields=["answer", "status", "answered_at", "answered_by", "updated_at"])
    context = {"reference": ticket.reference, "answer": ticket.answer[:900]}
    if ticket.user_id:
        notify(ticket.user, "help.ticket_answered", context, link="/aide")
    elif ticket.email:
        with translation.override(ticket.language or "fr"):
            subject = _("Your question %(reference)s") % {"reference": ticket.reference}
        send_direct("email", ticket.email, subject, ticket.answer)
    record("content.ticket_answered", ticket, actor=actor)
    return ticket
