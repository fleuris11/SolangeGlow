"""Printable QR codes of a pro's short link: PNG card, A4 poster (PDF), sticker sheet (PDF).

Drawn with Pillow at 300 dpi in the brand colours and fonts (Fraunces for the name,
Atkinson Hyperlegible Next for the rest). Texts are in the pro's language.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import segno
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from PIL import Image, ImageDraw, ImageFont

from .models import ProProfile

FONTS = Path(settings.BASE_DIR) / "assets" / "fonts"
DPI = 300
MM = DPI / 25.4

HIBISCUS = (200, 16, 46)
PRUNE = (59, 18, 51)
PRUNE_DOUX = (122, 78, 110)
LAIT = (255, 247, 245)
POUDRE = (249, 225, 231)
WHITE = (255, 255, 255)
OR = (232, 176, 75)


@lru_cache(maxsize=32)
def _font(family: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONTS / f"{family}.ttf"), size)
    axes = {axis["name"]: axis for axis in font.get_variation_axes()}
    values = []
    for name, axis in axes.items():
        wanted = {
            b"Weight": weight,
            b"Optical Size": min(144, max(9, size // 4)),
            b"Softness": 100,
            b"Wonky": 1,
        }.get(name, axis["default"])
        values.append(min(axis["maximum"], max(axis["minimum"], wanted)))
    font.set_variation_by_axes(values)
    return font


def display_font(size: int) -> ImageFont.FreeTypeFont:
    return _font("Fraunces", size, 800)


def text_font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    return _font("AtkinsonHyperlegibleNext", size, weight)


def qr_image(url: str, module_px: int) -> Image.Image:
    """The QR code (error correction Q: still readable when a little damaged or dirty)."""
    qr = segno.make(url, error="q", micro=False)
    matrix = qr.matrix
    count = len(matrix)
    border = 4
    side = (count + 2 * border) * module_px
    image = Image.new("RGB", (side, side), WHITE)
    draw = ImageDraw.Draw(image)
    finders = {(0, 0), (0, count - 7), (count - 7, 0)}

    def in_finder(row: int, col: int) -> bool:
        return any(r <= row < r + 7 and c <= col < c + 7 for r, c in finders)

    for row, line in enumerate(matrix):
        for col, dark in enumerate(line):
            if dark and not in_finder(row, col):
                x, y = (col + border) * module_px, (row + border) * module_px
                draw.rectangle([x, y, x + module_px - 1, y + module_px - 1], fill=PRUNE)
    # The three corner squares in hibiscus, slightly rounded: the brand touch.
    for r, c in finders:
        x, y = (c + border) * module_px, (r + border) * module_px
        unit = module_px
        draw.rounded_rectangle([x, y, x + 7 * unit - 1, y + 7 * unit - 1], 2 * unit, fill=HIBISCUS)
        draw.rounded_rectangle(
            [x + unit, y + unit, x + 6 * unit - 1, y + 6 * unit - 1], int(1.4 * unit), fill=WHITE
        )
        draw.rounded_rectangle(
            [x + 2 * unit, y + 2 * unit, x + 5 * unit - 1, y + 5 * unit - 1],
            unit,
            fill=HIBISCUS,
        )
    return image


def _petals(image: Image.Image, cx: int, cy: int, size: int) -> None:
    """Three lotus petals opening from one point (cx, cy), like the logo."""
    width, length = int(size * 0.62), int(size * 1.5)
    for angle in (-42, 0, 42):
        # Drawn upright on a canvas centred on the base point, then turned around it.
        canvas = Image.new("RGBA", (length * 2, length * 2), (0, 0, 0, 0))
        ImageDraw.Draw(canvas).ellipse(
            [length - width // 2, 0, length + width // 2, length], fill=(*HIBISCUS, 255)
        )
        turned = canvas.rotate(-angle, resample=Image.Resampling.BICUBIC, center=(length, length))
        image.paste(turned, (cx - length, cy - length), turned)


def _wordmark(image: Image.Image, cx: int, top: int, size: int) -> int:
    """Petals + « Solange Glow »; returns the bottom of the drawing."""
    _petals(image, cx, top + size, size // 2 + size // 6)
    draw = ImageDraw.Draw(image)
    font = display_font(size)
    draw.text((cx, top + size + size // 4), "Solange Glow", font=font, fill=HIBISCUS, anchor="mt")
    return top + size + size // 4 + int(size * 1.1)


def _centered(draw, cx, y, text, font, fill, max_width) -> int:
    """Draws centred text on as many lines as needed; returns the next y."""
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_height = int(font.size * 1.2)
    for line in lines:
        draw.text((cx, y), line, font=font, fill=fill, anchor="mt")
        y += line_height
    return y


def _fitting(draw, text: str, max_width: int, size: int) -> ImageFont.FreeTypeFont:
    """The biggest display font (down to a third of `size`) that fits on one line."""
    while size > 20 and draw.textlength(text, font=display_font(size)) > max_width:
        size -= 2
    return display_font(size)


def _trades(pro: ProProfile) -> str:
    return ", ".join(trade.name for trade in pro.trades.all()[:3])


def _url(pro: ProProfile) -> str:
    from .services import short_link

    return short_link(pro)


def _language(pro: ProProfile) -> str:
    return pro.user.preferred_language or settings.LANGUAGE_CODE


def card_png(pro: ProProfile) -> bytes:
    """Square-ish card for social networks and WhatsApp status: QR, name, trades, link."""
    with translation.override(_language(pro)):
        width, height = 1200, 1500
        image = Image.new("RGB", (width, height), LAIT)
        draw = ImageDraw.Draw(image)
        y = _wordmark(image, width // 2, 40, 64)
        y = _centered(draw, width // 2, y + 10, pro.display_name, display_font(76), PRUNE, 1060)
        y = _centered(draw, width // 2, y, _trades(pro), text_font(40, 700), PRUNE_DOUX, 1060)
        qr = qr_image(_url(pro), 22)
        qr = qr.resize((820, 820), Image.Resampling.NEAREST)
        top = y + 30
        draw.rounded_rectangle(
            [width // 2 - 440, top - 20, width // 2 + 440, top + 840], 48, fill=WHITE
        )
        image.paste(qr, (width // 2 - 410, top))
        link = _url(pro).split("://", 1)[-1]
        draw.text(
            (width // 2, top + 870), link, font=text_font(44, 700), fill=HIBISCUS, anchor="mt"
        )
        buffer = io.BytesIO()
        image.save(buffer, "PNG", optimize=True)
        return buffer.getvalue()


def poster_pdf(pro: ProProfile) -> bytes:
    """A4 poster to stick in the salon: « Book with … », big QR, link, how to scan."""
    return _pdf(poster_image(pro))


def stickers_pdf(pro: ProProfile) -> bytes:
    """A4 sheet of 6 round stickers (8.5 cm), with a dotted line to cut along."""
    return _pdf(stickers_image(pro))


def _pdf(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PDF", resolution=DPI, quality=95)
    return buffer.getvalue()


def poster_image(pro: ProProfile) -> Image.Image:
    with translation.override(_language(pro)):
        width, height = int(210 * MM), int(297 * MM)
        image = Image.new("RGB", (width, height), LAIT)
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, width, int(18 * MM)], fill=HIBISCUS)
        y = _wordmark(image, width // 2, int(26 * MM), 120)
        y = _centered(
            draw,
            width // 2,
            y + 40,
            _("Book an appointment with"),
            text_font(80),
            PRUNE,
            width - 300,
        )
        y = _centered(
            draw, width // 2, y + 10, pro.display_name, display_font(170), PRUNE, width - 300
        )
        y = _centered(
            draw, width // 2, y + 10, _trades(pro), text_font(76, 700), PRUNE_DOUX, width - 300
        )
        side = int(118 * MM)
        qr = qr_image(_url(pro), 40).resize((side, side), Image.Resampling.NEAREST)
        top = y + 60
        draw.rounded_rectangle(
            [(width - side) // 2 - 60, top - 60, (width + side) // 2 + 60, top + side + 60],
            90,
            fill=WHITE,
            outline=POUDRE,
            width=12,
        )
        image.paste(qr, ((width - side) // 2, top))
        y = top + side + 110
        y = _centered(
            draw,
            width // 2,
            y,
            _("Scan with the camera of your phone"),
            text_font(72, 700),
            PRUNE,
            width - 300,
        )
        link = _url(pro).split("://", 1)[-1]
        _centered(draw, width // 2, y + 20, link, text_font(84, 800), HIBISCUS, width - 200)
        draw.rectangle([0, height - int(12 * MM), width, height], fill=POUDRE)
        return image


def stickers_image(pro: ProProfile) -> Image.Image:
    with translation.override(_language(pro)):
        width, height = int(210 * MM), int(297 * MM)
        image = Image.new("RGB", (width, height), WHITE)
        draw = ImageDraw.Draw(image)
        diameter = int(85 * MM)
        qr_side = int(diameter * 0.52)
        qr = qr_image(_url(pro), 24).resize((qr_side, qr_side), Image.Resampling.NEAREST)
        gap_x = (width - 2 * diameter) // 3
        gap_y = (height - 3 * diameter) // 4
        name_font = _fitting(draw, pro.display_name, int(diameter * 0.6), 60)
        small = text_font(44, 700)
        for row in range(3):
            for col in range(2):
                left = gap_x + col * (diameter + gap_x)
                top = gap_y + row * (diameter + gap_y)
                cx = left + diameter // 2
                box = [left, top, left + diameter, top + diameter]
                draw.ellipse(box, fill=POUDRE)
                # Cutting guide.
                draw.arc(
                    [box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8],
                    0,
                    360,
                    fill=PRUNE_DOUX,
                    width=2,
                )
                draw.text(
                    (cx, top + int(diameter * 0.15)),
                    pro.display_name,
                    font=name_font,
                    fill=PRUNE,
                    anchor="mm",
                )
                qr_top = top + int(diameter * 0.24)
                draw.rounded_rectangle(
                    [
                        cx - qr_side // 2 - 16,
                        qr_top - 16,
                        cx + qr_side // 2 + 16,
                        qr_top + qr_side + 16,
                    ],
                    28,
                    fill=WHITE,
                )
                image.paste(qr, (cx - qr_side // 2, qr_top))
                draw.text(
                    (cx, qr_top + qr_side + 36),
                    _("Scan me to book"),
                    font=small,
                    fill=HIBISCUS,
                    anchor="mt",
                )
        return image
