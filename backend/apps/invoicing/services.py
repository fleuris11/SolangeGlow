"""Issuing invoices, receipts and credit notes (continuous numbers, never changed)."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.audit.services import record
from apps.core.errors import DomainError

from .einvoice import provider
from .models import Document, Issuer, Sequence

K = Document.Kind
PREFIX = {K.INVOICE: "F", K.RECEIPT: "R", K.CREDIT_NOTE: "A"}


class InvalidDocument(DomainError):
    code = "invalid_document"
    message = _("A document needs at least one line with an amount.")


class DocumentNotFound(DomainError):
    code = "document_not_found"
    status_code = 404
    message = _("This document does not exist or is not yours.")


class AlreadyCredited(DomainError):
    code = "already_credited"
    message = _("This document was already cancelled by a credit note.")


def issuer_for(pro) -> Issuer:
    issuer, _created = Issuer.objects.get_or_create(
        pro=pro,
        defaults={
            "legal_name": pro.display_name,
            "address": ", ".join(filter(None, (pro.address, pro.district, pro.city))),
            "country_id": pro.country_id,
        },
    )
    return issuer


def platform_issuer() -> Issuer:
    issuer, _ = Issuer.objects.get_or_create(
        is_platform=True, defaults={"legal_name": "Solange Glow"}
    )
    return issuer


def update_issuer(pro, **changes) -> Issuer:
    issuer = issuer_for(pro)
    for field in (
        "legal_name",
        "address",
        "registration",
        "vat_number",
        "vat_rate_bps",
        "vat_mention",
        "footer",
    ):
        if field in changes:
            setattr(issuer, field, changes[field])
    issuer.full_clean(exclude=["pro", "country"])
    issuer.save()
    return issuer


def _next_number(issuer: Issuer, kind: str, year: int) -> str:
    prefix = PREFIX[kind]
    try:
        with transaction.atomic():
            Sequence.objects.get_or_create(issuer=issuer, prefix=prefix, year=year)
    except IntegrityError:  # created at the same moment by another document
        pass
    sequence = Sequence.objects.select_for_update().get(issuer=issuer, prefix=prefix, year=year)
    sequence.last_number += 1
    sequence.save(update_fields=["last_number", "updated_at"])
    return f"{prefix}-{year}-{sequence.last_number:06d}"


def tax_of(total_minor: int, rate_bps: int) -> int:
    """VAT included in a price (prices are shown taxes included)."""
    if not rate_bps:
        return 0
    before_tax = (total_minor * 10_000 * 2 + (10_000 + rate_bps)) // (2 * (10_000 + rate_bps))
    return total_minor - before_tax


def _clean_lines(lines: list[dict]) -> list[dict]:
    cleaned = []
    for line in lines:
        quantity = int(line.get("quantity", 1))
        unit = int(line["unit_minor"])
        cleaned.append(
            {
                "label": str(line["label"])[:150],
                "quantity": quantity,
                "unit_minor": unit,
                "total_minor": quantity * unit,
            }
        )
    if not cleaned or sum(line["total_minor"] for line in cleaned) == 0:
        raise InvalidDocument()
    return cleaned


@transaction.atomic
def issue(
    issuer: Issuer,
    kind: str,
    *,
    buyer_name: str,
    lines: list[dict],
    currency: str,
    buyer_details: str = "",
    buyer_user=None,
    paid_with: str = "",
    source_type: str = "",
    source_id=None,
    corrects: Document | None = None,
) -> Document:
    lines = _clean_lines(lines)
    total = sum(line["total_minor"] for line in lines)
    now = timezone.now()
    document = Document.objects.create(
        issuer=issuer,
        kind=kind,
        number=_next_number(issuer, kind, now.year),
        issued_at=now,
        buyer_name=(buyer_name or "—")[:150],
        buyer_details=(buyer_details or "")[:255],
        buyer_user=buyer_user,
        lines=lines,
        currency=currency,
        total_minor=total,
        tax_minor=tax_of(total, issuer.vat_rate_bps),
        paid_with=paid_with[:60],
        source_type=source_type,
        source_id=source_id,
        corrects=corrects,
    )
    record("invoicing.issued", document, metadata={"number": document.number})
    return document


def for_source(source_type: str, source_id, kind: str) -> Document | None:
    return Document.objects.filter(
        source_type=source_type, source_id=source_id, kind=kind, corrects__isnull=True
    ).first()


def issue_once(issuer: Issuer, kind: str, *, source_type: str, source_id, **values) -> Document:
    """The document of a sale, issued the first time it is asked (then always the same)."""
    found = for_source(source_type, source_id, kind)
    if found is not None:
        return found
    return issue(issuer, kind, source_type=source_type, source_id=source_id, **values)


@transaction.atomic
def credit(document: Document, *, actor=None, reason: str = "") -> Document:
    """Cancels a document: a credit note with the same lines, negative."""
    document = Document.objects.select_for_update().get(pk=document.pk)
    if document.kind == K.CREDIT_NOTE or document.credit_notes.exists():
        raise AlreadyCredited()
    lines = [
        {"label": line["label"], "quantity": line["quantity"], "unit_minor": -line["unit_minor"]}
        for line in document.lines
    ]
    note = issue(
        document.issuer,
        K.CREDIT_NOTE,
        buyer_name=document.buyer_name,
        buyer_details=document.buyer_details,
        buyer_user=document.buyer_user,
        lines=lines,
        currency=document.currency,
        source_type=document.source_type,
        source_id=document.source_id,
        corrects=document,
    )
    record("invoicing.credited", document, actor=actor, metadata={"reason": reason[:200]})
    return note


def send_electronic(document: Document) -> Document:
    """To the approved platform (none connected yet: the document stays « not sent »)."""
    result = provider().send(document)
    document.einvoice_status = result.status
    document.einvoice_reference = result.reference
    document.save(update_fields=["einvoice_status", "einvoice_reference", "updated_at"])
    return document
