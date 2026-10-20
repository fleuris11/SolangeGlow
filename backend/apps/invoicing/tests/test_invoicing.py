"""Invoices and receipts: continuous numbers, never changed, cancelled by a credit note,
VAT included, PDF, electronic sending not connected."""

import pytest
from django.utils import timezone

from apps.booking.tests.factories import salon
from apps.invoicing import einvoice, pdf, services
from apps.invoicing.models import Document

pytestmark = pytest.mark.django_db
K = Document.Kind
LINES = [{"label": "Coloration", "quantity": 1, "unit_minor": 20_000}]


def issue(issuer, **values):
    return services.issue(
        issuer,
        values.pop("kind", K.INVOICE),
        buyer_name="Awa",
        lines=LINES,
        currency="XOF",
        **values,
    )


def test_numbers_follow_each_other_per_series():
    issuer = services.issuer_for(salon())
    year = timezone.now().year
    first, second = issue(issuer), issue(issuer)
    receipt = issue(issuer, kind=K.RECEIPT)
    assert [first.number, second.number] == [f"F-{year}-000001", f"F-{year}-000002"]
    assert receipt.number == f"R-{year}-000001"
    other = services.issuer_for(salon("Autre salon"))
    assert issue(other).number == f"F-{year}-000001"  # each pro has her own series


def test_a_document_never_changes_a_credit_note_cancels_it():
    issuer = services.issuer_for(salon())
    invoice = issue(issuer)
    invoice.buyer_name = "Quelqu'un d'autre"
    with pytest.raises(ValueError):
        invoice.save()
    with pytest.raises(ValueError):
        invoice.delete()
    note = services.credit(invoice, reason="Erreur de prix")
    assert note.kind == K.CREDIT_NOTE and note.corrects == invoice
    assert note.total_minor == -20_000 and note.number.startswith("A-")
    with pytest.raises(services.AlreadyCredited):
        services.credit(invoice)


def test_vat_included_and_the_mention_without_vat():
    pro = salon()
    issuer = services.update_issuer(pro, legal_name="Salon Estelle SARL", vat_rate_bps=2000)
    invoice = issue(issuer)
    assert invoice.tax_minor == 3_333  # 20 000 taxes included, 20 %: 16 667 + 3 333
    assert services.tax_of(12_000, 0) == 0
    with pytest.raises(services.InvalidDocument):
        services.issue(issuer, K.INVOICE, buyer_name="Awa", lines=[], currency="XOF")


def test_the_pdf_and_the_electronic_sending():
    pro = salon()
    issuer = services.update_issuer(
        pro,
        legal_name="Salon Estelle",
        registration="IFU 3202312345678",
        vat_mention="TVA non applicable, art. 293 B du CGI",
    )
    invoice = issue(issuer, paid_with="Espèces")
    content = pdf.render(invoice)
    assert content.startswith(b"%PDF") and len(content) > 5_000
    assert not einvoice.is_connected()
    services.send_electronic(invoice)
    invoice.refresh_from_db()
    assert invoice.einvoice_status == Document.EInvoice.NOT_SENT


def test_one_document_per_sale():
    issuer = services.issuer_for(salon())
    values = {"source_type": "booking", "source_id": issuer.pk, "buyer_name": "Awa", "lines": LINES}
    first = services.issue_once(issuer, K.INVOICE, currency="XOF", **values)
    assert services.issue_once(issuer, K.INVOICE, currency="XOF", **values) == first
