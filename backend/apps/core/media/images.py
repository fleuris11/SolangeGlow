"""Picture pipeline: checked, re-encoded in WebP, several sizes, no metadata, blur preview."""

from __future__ import annotations

import io

import blurhash
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from apps.core.selectors import get_setting

ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO", "GIF"}
DEFAULT_SIZES = {"thumb": 160, "medium": 640, "large": 1280}


class InvalidImage(Exception):
    pass


def open_image(data: bytes) -> Image.Image:
    """Opens untrusted bytes; refuses anything that is not a real picture."""
    try:
        probe = Image.open(io.BytesIO(data))
        if probe.format not in ACCEPTED_FORMATS:
            raise InvalidImage(f"format {probe.format}")
        probe.verify()
        image = Image.open(io.BytesIO(data))
        image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError) as exc:  # OSError: unidentified
        raise InvalidImage(str(exc)) from exc
    # Turn the picture upright, then forget every metadata (EXIF, GPS, ICC).
    image = ImageOps.exif_transpose(image)
    return image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")


def compute_blurhash(image: Image.Image) -> str:
    small = image.convert("RGB").copy()
    small.thumbnail((32, 32))
    raw = small.tobytes()
    pixels = [tuple(raw[i : i + 3]) for i in range(0, len(raw), 3)]
    rows = [pixels[y * small.width : (y + 1) * small.width] for y in range(small.height)]
    return blurhash.encode(rows, components_x=4, components_y=3)


def render_variants(image: Image.Image, save, *, prefix: str = "") -> dict:
    """Writes one WebP per size (never larger than the original). `save(name, content)`."""
    sizes = get_setting("media.image_sizes", default=DEFAULT_SIZES)
    quality = int(get_setting("media.webp_quality", default=80))
    variants = {}
    for name, max_side in sorted(sizes.items(), key=lambda item: item[1]):
        copy = image.copy()
        copy.thumbnail((int(max_side), int(max_side)), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        copy.save(buffer, "WEBP", quality=quality, method=4)  # no exif/icc: dropped
        data = buffer.getvalue()
        variant = f"{prefix}{name}"
        path = save(f"{variant}.webp", ContentFile(data))
        variants[variant] = {
            "path": path,
            "width": copy.width,
            "height": copy.height,
            "bytes": len(data),
            "content_type": "image/webp",
        }
    return variants
