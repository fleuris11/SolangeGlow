"""Real photographs for the demonstration data (development only, through seed_demo).

Same files and credits as web/public/media (web/scripts/media-sources.json). The people shown
are not pros registered on the platform: they only illustrate the demo accounts.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

FOLDER = Path(settings.BASE_DIR) / "assets" / "demo-media"
SIDE = 1200
QUALITY = 84

TRADES = {
    "braids": [
        "braids-yellow",
        "braids-hoops",
        "braids-lilac",
        "cornrows-glasses",
        "cornrows-side",
        "cornrows-down",
        "braids-top",
        "braider-hands",
    ],
    "hair": [
        "hero-afro-profile",
        "curls-teal",
        "curls-blue",
        "curls-hands",
        "red-hair-wall",
        "locs-light",
        "locs-sit",
        "salon-pink",
    ],
    "makeup": ["makeup-portrait", "lips-orange", "locs-beauty", "bride-makeup", "bride-afro"],
    "nails": ["nails-lips", "nails-pro"],
    "sewing": ["sewing", "fashion-coat", "wax-rolls", "wax-blue", "sisters-yellow", "afro-jacket"],
    "headwrap": ["headwrap-smile", "headwrap-mural", "hero-orange-hat", "portrait-white"],
    "skincare": ["skin-warm", "skin-profile", "locs-skin", "portrait-white"],
}
PORTRAITS = ["headwrap-smile", "woman-door", "curls-blue", "braids-hoops", "skin-warm"]
# The drawing a demo product asked for → the closest real photograph.
PRODUCTS = {
    "palette": "palette",
    "lipstick": "lips-orange",
    "polish": "nails-pro",
    "fabric": "wax-rolls",
    "wig": "curls-hands",
    "bottle": "brushes",
    "jar": "brushes",
    "perfume": "palette",
}


def _pick(names: list[str], seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).digest()
    return names[int.from_bytes(digest[:4], "big") % len(names)]


def _jpeg(name: str, *, faded: bool = False) -> bytes | None:
    path = FOLDER / f"{name}.jpg"
    if not path.exists():
        return None
    image = Image.open(path).convert("RGB")
    image.thumbnail((SIDE, SIDE))
    if faded:
        image = ImageOps.autocontrast(ImageOps.grayscale(image)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=QUALITY)
    return buffer.getvalue()


def look(seed: str, trade: str, *, stage: str = "after") -> bytes | None:
    """A photo of a look for this trade; `None` when the file is missing (then it is drawn)."""
    return _jpeg(_pick(TRADES.get(trade) or TRADES["hair"], seed), faded=stage == "before")


def portrait(seed: str, trade: str) -> bytes | None:
    return _jpeg(_pick(TRADES.get(trade) or PORTRAITS, f"portrait-{seed}"))


def product(seed: str, drawing: str) -> bytes | None:
    name = PRODUCTS.get(drawing)
    return _jpeg(name) if name else None
