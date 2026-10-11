"""Identity documents vault (ADR-005): pictures cleaned, then encrypted before storage.

The key comes from IDENTITY_VAULT_KEY (a Fernet key); in development only, a key is
derived from SECRET_KEY. Nothing here produces a link: files are read by the admin
through a view that checks the permission and records each access.
"""

from __future__ import annotations

import base64
import hashlib
import io

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

from apps.core.media.images import InvalidImage, open_image

MAX_SIDE = 2000


def _fernet() -> Fernet:
    if settings.IDENTITY_VAULT_KEY:
        return Fernet(settings.IDENTITY_VAULT_KEY.encode())
    digest = hashlib.sha256(f"solangeglow-vault|{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal_image(uploaded) -> ContentFile:
    """Checks it is a real picture, removes its metadata (GPS…), re-encodes and encrypts it."""
    data = uploaded.read()
    image = open_image(data)  # raises InvalidImage
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    return ContentFile(_fernet().encrypt(buffer.getvalue()), name="document.bin")


def open_sealed(field) -> bytes:
    """Decrypted JPEG bytes of a vault file."""
    with field.open("rb") as handle:
        token = handle.read()
    try:
        return _fernet().decrypt(token)
    except InvalidToken as exc:  # wrong key or damaged file
        raise InvalidImage("vault file cannot be decrypted") from exc
