"""Illustrated pictures for the demo data (no real photo before the pros post theirs).

Flat drawings in the brand palette: a portrait with a hairstyle, a headwrap or a makeup,
hands with polished nails, a wax dress, a skincare scene. Deterministic for a given seed.
"""

from __future__ import annotations

import io
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1350
SKINS = [(241, 201, 165), (198, 138, 94), (160, 102, 63), (122, 74, 44), (79, 46, 28)]
BACKGROUNDS = [(249, 225, 231), (255, 247, 245), (246, 230, 200), (226, 240, 232), (238, 228, 245)]
ACCENTS = [(200, 16, 46), (232, 176, 75), (31, 122, 90), (59, 18, 51), (122, 78, 110)]
HAIR = (36, 16, 24)
LIPS = [(170, 30, 60), (200, 16, 46), (140, 60, 70), (190, 90, 90)]


def _rng(seed: str) -> random.Random:
    return random.Random(seed)  # noqa: S311  (pictures, not security)


def _portrait(draw: ImageDraw.ImageDraw, rng: random.Random, skin, outfit) -> tuple[int, int]:
    cx, cy = W // 2, 560
    draw.rounded_rectangle([cx - 330, 980, cx + 330, H + 60], 180, fill=outfit)  # shoulders
    draw.rectangle([cx - 70, 760, cx + 70, 1000], fill=skin)  # neck
    draw.ellipse([cx - 200, cy - 250, cx + 200, cy + 250], fill=skin)  # face
    return cx, cy


def _face(draw, rng, cx, cy, skin, *, makeup=False):
    eye = (40, 22, 26)
    for side in (-1, 1):
        x = cx + side * 80
        if makeup:
            shade = rng.choice([(200, 120, 60), (150, 60, 120), (232, 176, 75)])
            draw.ellipse([x - 60, cy - 70, x + 60, cy - 10], fill=shade)
        draw.ellipse([x - 30, cy - 45, x + 30, cy - 15], fill=(255, 255, 255))
        draw.ellipse([x - 14, cy - 42, x + 14, cy - 16], fill=eye)
        draw.line([x - 45, cy - 85, x + 45, cy - 95], fill=HAIR, width=10)
    lips = rng.choice(LIPS) if makeup else tuple(max(0, c - 40) for c in skin)
    draw.chord([cx - 70, cy + 80, cx + 70, cy + 150], 0, 180, fill=lips)
    draw.chord([cx - 70, cy + 60, cx + 70, cy + 120], 180, 360, fill=lips)
    if makeup:
        glow = tuple(min(255, c + 40) for c in skin)
        for side in (-1, 1):
            draw.ellipse([cx + side * 130 - 45, cy + 20, cx + side * 130 + 45, cy + 70], fill=glow)


def _hair(draw, rng, cx, cy, style: str, accent):
    if style == "short":
        draw.ellipse([cx - 225, cy - 300, cx + 225, cy - 60], fill=HAIR)
    elif style == "afro":
        draw.ellipse([cx - 360, cy - 420, cx + 360, cy + 120], fill=HAIR)
    elif style == "bun":
        draw.ellipse([cx - 220, cy - 290, cx + 220, cy - 80], fill=HAIR)
        draw.ellipse([cx - 110, cy - 470, cx + 110, cy - 250], fill=HAIR)
    elif style in ("braids", "knotless"):
        width = 34 if style == "braids" else 24
        draw.ellipse([cx - 230, cy - 300, cx + 230, cy - 70], fill=HAIR)
        x = cx - 330
        while x <= cx + 330:
            if abs(x - cx) > 120:
                bottom = rng.randint(1100, 1300)
                draw.rounded_rectangle([x, cy - 120, x + width, bottom], width // 2, fill=HAIR)
                if rng.random() < 0.25:
                    draw.ellipse([x - 4, bottom - 20, x + width + 4, bottom + 24], fill=accent)
            x += width + 6
    elif style == "relaxed":
        draw.ellipse([cx - 240, cy - 300, cx + 240, cy - 40], fill=HAIR)
        draw.rounded_rectangle([cx - 290, cy - 150, cx - 170, cy + 520], 60, fill=HAIR)
        draw.rounded_rectangle([cx + 170, cy - 150, cx + 290, cy + 520], 60, fill=HAIR)


def _headwrap(draw, rng, cx, cy, accent, second):
    draw.ellipse([cx - 280, cy - 470, cx + 280, cy - 60], fill=accent)
    for _ in range(3):
        x = cx + rng.randint(-200, 200)
        draw.ellipse([x - 120, cy - 560, x + 120, cy - 330], fill=accent)
    for _ in range(18):
        x, y = cx + rng.randint(-240, 240), cy + rng.randint(-480, -100)
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=second)


def _nails(draw, rng, skin, accent):
    for index in range(5):
        x = 250 + index * 130
        top = 420 + abs(2 - index) * 70
        draw.rounded_rectangle([x, top, x + 100, 1150], 50, fill=skin)
        draw.rounded_rectangle([x + 14, top + 10, x + 86, top + 130], 36, fill=accent)
        draw.ellipse([x + 30, top + 30, x + 50, top + 50], fill=(255, 255, 255))
    draw.rounded_rectangle([200, 950, 900, 1350], 120, fill=skin)


def _dress(draw, rng, accent, second):
    draw.polygon([(540, 260), (360, 420), (260, 1250), (820, 1250), (720, 420)], fill=accent)
    for _ in range(60):
        x, y = rng.randint(300, 780), rng.randint(450, 1220)
        size = rng.randint(14, 30)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=second)
    draw.rectangle([380, 600, 700, 650], fill=second)


def _skincare(draw, rng, accent):
    draw.rounded_rectangle([370, 620, 710, 1120], 70, fill=(255, 255, 255))
    draw.rounded_rectangle([340, 540, 740, 650], 40, fill=accent)
    draw.rounded_rectangle([430, 760, 650, 900], 20, fill=tuple(min(255, c + 60) for c in accent))
    for _ in range(12):
        x, y = rng.randint(150, 930), rng.randint(150, 500)
        draw.regular_polygon((x, y, rng.randint(10, 22)), 4, rotation=45, fill=(232, 176, 75))


def picture(seed: str, trade: str, *, stage: str = "after") -> bytes:
    """A JPEG of a look. `stage` is "before" (plain) or "after" (the work of the pro)."""
    rng = _rng(f"{seed}:{trade}")
    background = rng.choice(BACKGROUNDS) if stage == "after" else (236, 231, 229)
    image = Image.new("RGB", (W, H), background)
    draw = ImageDraw.Draw(image)
    skin = rng.choice(SKINS)
    accent, second = rng.sample(ACCENTS, 2)

    if trade == "nails":
        _nails(draw, rng, skin, accent if stage == "after" else tuple(c - 20 for c in skin))
    elif trade == "sewing":
        _dress(draw, rng, accent if stage == "after" else (210, 205, 200), second)
    elif trade == "skincare" and stage == "after" and rng.random() < 0.5:
        _skincare(draw, rng, accent)
    else:
        styles = {"braids": ["braids", "knotless"], "hair": ["afro", "bun", "relaxed"]}
        style = rng.choice(styles.get(trade, ["short", "bun", "afro"]))
        if stage == "before":
            style = "short"
        cx, cy = _portrait(draw, rng, skin, accent if stage == "after" else (180, 170, 165))
        if trade == "headwrap" and stage == "after":
            _headwrap(draw, rng, cx, cy, accent, second)
        else:
            _hair(draw, rng, cx, cy, style, second)
        _face(
            draw, rng, cx, cy, skin, makeup=(trade in ("makeup", "skincare") and stage == "after")
        )

    image = image.filter(ImageFilter.SMOOTH)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=86)
    return buffer.getvalue()
