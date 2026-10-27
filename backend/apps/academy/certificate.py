"""The certificate of a finished course: A4 landscape, brand fonts, a QR code that opens the
public page where anybody can check it."""

from __future__ import annotations

import io

import segno
from django.conf import settings
from django.utils import formats, translation
from django.utils.translation import gettext as _
from fpdf import FPDF

from apps.invoicing.pdf import HIBISCUS, PRUNE, PRUNE_DOUX, TRAIT, _static_font

from .models import Certificate


def check_url(certificate: Certificate, language: str = "fr") -> str:
    return f"{settings.SITE_URL.rstrip('/')}/{language}/certificat/{certificate.code}"


def render(certificate: Certificate, language: str = "fr") -> bytes:
    with translation.override(language):
        return _render(certificate, language)


def _render(certificate: Certificate, language: str) -> bytes:
    pdf = FPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("text", "", _static_font("AtkinsonHyperlegibleNext", 400))
    pdf.add_font("text", "B", _static_font("AtkinsonHyperlegibleNext", 700))
    pdf.add_font("display", "", _static_font("Fraunces", 800))
    pdf.set_title(_("Certificate %(code)s") % {"code": certificate.code})
    pdf.set_author("Solange Glow")
    pdf.add_page()
    width = pdf.w

    # A thin frame in the colour of the lines.
    pdf.set_draw_color(*TRAIT)
    pdf.set_line_width(1.2)
    pdf.rect(10, 10, width - 20, pdf.h - 20)

    pdf.set_y(28)
    pdf.set_text_color(*HIBISCUS)
    pdf.set_font("display", size=16)
    pdf.cell(0, 8, "Solange Glow Académie", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_text_color(*PRUNE)
    pdf.set_font("display", size=34)
    pdf.cell(0, 16, _("Certificate of training"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.set_font("text", size=13)
    pdf.cell(0, 8, _("This certifies that"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*PRUNE)
    pdf.set_font("display", size=26)
    pdf.cell(0, 14, certificate.holder_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.set_font("text", size=13)
    pdf.cell(0, 8, _("finished the course"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*PRUNE)
    pdf.set_font("text", "B", size=18)
    pdf.multi_cell(0, 9, certificate.course_title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.set_font("text", size=12)
    issued = formats.date_format(certificate.issued_at, "j F Y")
    pdf.cell(
        0,
        8,
        _("With %(trainer)s, on %(date)s") % {"trainer": certificate.trainer_name, "date": issued},
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    # QR code and code, bottom right: anybody can check it.
    url = check_url(certificate, language)
    image = io.BytesIO()
    segno.make(url, error="q", micro=False).save(image, kind="png", scale=6, border=2)
    image.seek(0)
    size = 34
    pdf.image(image, x=width - 22 - size, y=pdf.h - 22 - size, w=size, h=size)
    pdf.set_xy(22, pdf.h - 36)
    pdf.set_font("text", "B", size=11)
    pdf.set_text_color(*PRUNE)
    pdf.cell(0, 6, _("Code: %(code)s") % {"code": certificate.code}, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(22)
    pdf.set_font("text", size=10)
    pdf.set_text_color(*PRUNE_DOUX)
    pdf.cell(0, 6, _("Check it: %(url)s") % {"url": url})
    return bytes(pdf.output())
