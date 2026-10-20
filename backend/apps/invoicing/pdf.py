"""The PDF of an invoice, receipt or credit note: real text (searchable), A4, brand fonts.

Drawn again from the stored document each time: what is printed is what was issued.
"""

from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.utils import formats, translation
from django.utils.translation import gettext as _
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fpdf import FPDF

from apps.core.money import Money

from .models import Document

FONTS = Path(settings.BASE_DIR) / "assets" / "fonts"
PRUNE = (59, 18, 51)
PRUNE_DOUX = (122, 78, 110)
HIBISCUS = (200, 16, 46)
TRAIT = (235, 217, 222)
NARROW, NBSP = chr(0x202F), chr(0xA0)  # spaces of the money format, not in every font

TITLES = {
    Document.Kind.INVOICE: "Invoice",
    Document.Kind.RECEIPT: "Receipt",
    Document.Kind.CREDIT_NOTE: "Credit note",
}


@lru_cache(maxsize=8)
def _static_font(family: str, weight: int) -> str:
    """The brand fonts are variable: a fixed instance for the PDF (made once, cached)."""
    target = Path(tempfile.gettempdir()) / f"solangeglow-{family}-{weight}.ttf"
    if not target.exists():
        font = TTFont(str(FONTS / f"{family}.ttf"))
        axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
        axes["wght"] = weight
        instancer.instantiateVariableFont(font, axes, inplace=True)
        font.save(str(target))
    return str(target)


def _money(value: int, currency: str, language: str) -> str:
    # The narrow no-break spaces of the formatter are not in every PDF font.
    return Money(value, currency).format(language).replace(NARROW, " ").replace(NBSP, " ")


def render(document: Document, language: str = "fr") -> bytes:
    with translation.override(language):
        return _render(document, language)


def _render(document: Document, language: str) -> bytes:
    issuer = document.issuer
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("text", "", _static_font("AtkinsonHyperlegibleNext", 400))
    pdf.add_font("text", "B", _static_font("AtkinsonHyperlegibleNext", 700))
    pdf.add_font("display", "", _static_font("Fraunces", 800))
    pdf.set_title(f"{_(TITLES[document.kind])} {document.number}")
    pdf.set_author(issuer.legal_name or "Solange Glow")
    pdf.add_page()

    # Issuer.
    pdf.set_text_color(*HIBISCUS)
    pdf.set_font("display", size=22)
    pdf.cell(0, 12, issuer.legal_name or "Solange Glow", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.set_font("text", size=10)
    for line in (
        issuer.address,
        issuer.registration and _("Company number: %(number)s") % {"number": issuer.registration},
        issuer.vat_number and _("VAT number: %(number)s") % {"number": issuer.vat_number},
    ):
        if line:
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

    # Title, number, date.
    pdf.ln(8)
    pdf.set_text_color(*PRUNE)
    pdf.set_font("display", size=18)
    pdf.cell(0, 10, f"{_(TITLES[document.kind])} {document.number}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("text", size=11)
    issued = formats.date_format(document.issued_at, "j F Y")
    pdf.cell(0, 6, _("Date: %(date)s") % {"date": issued}, new_x="LMARGIN", new_y="NEXT")
    if document.corrects_id:
        pdf.cell(
            0,
            6,
            _("Cancels %(number)s") % {"number": document.corrects.number},
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # Buyer.
    pdf.ln(4)
    pdf.set_font("text", "B", size=11)
    pdf.cell(0, 6, _("Client"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("text", size=11)
    pdf.cell(0, 6, document.buyer_name, new_x="LMARGIN", new_y="NEXT")
    if document.buyer_details:
        pdf.cell(0, 6, document.buyer_details, new_x="LMARGIN", new_y="NEXT")

    # Lines.
    pdf.ln(6)
    widths = (100, 20, 35, 35)
    pdf.set_draw_color(*TRAIT)
    pdf.set_font("text", "B", size=10)
    for width, label, align in zip(
        widths, (_("Description"), _("Qty"), _("Unit price"), _("Total")), "LRRR", strict=True
    ):
        pdf.cell(width, 8, label, border="B", align=align)
    pdf.ln()
    pdf.set_font("text", size=10)
    currency = document.currency
    for line in document.lines:
        cells = (
            line["label"],
            str(line["quantity"]),
            _money(line["unit_minor"], currency, language),
            _money(line["total_minor"], currency, language),
        )
        for width, value, align in zip(widths, cells, "LRRR", strict=True):
            pdf.cell(width, 8, value, border="B", align=align)
        pdf.ln()

    # Totals.
    pdf.ln(4)
    pdf.set_font("text", "B", size=12)
    pdf.cell(155, 8, _("Total, taxes included"), align="R")
    pdf.cell(35, 8, _money(document.total_minor, currency, language), align="R")
    pdf.ln()
    pdf.set_font("text", size=10)
    if document.tax_minor:
        pdf.cell(155, 6, _("of which VAT"), align="R")
        pdf.cell(35, 6, _money(document.tax_minor, currency, language), align="R")
        pdf.ln()
    elif issuer.vat_mention:
        pdf.cell(0, 6, issuer.vat_mention, align="R", new_x="LMARGIN", new_y="NEXT")
    if document.paid_with:
        pdf.cell(
            0,
            6,
            _("Paid with: %(means)s") % {"means": document.paid_with},
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # Footer.
    pdf.set_y(-30)
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.set_font("text", size=8)
    if issuer.footer:
        pdf.multi_cell(0, 4, issuer.footer, align="C")
    pdf.multi_cell(0, 4, _("Issued with Solange Glow."), align="C")
    return bytes(pdf.output())
