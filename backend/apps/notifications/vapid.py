"""VAPID keys for Web Push. In development they are created once in backend/.vapid.json."""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from django.conf import settings
from py_vapid import Vapid01

from apps.core.providers import ProviderNotConfigured

DEV_KEYS_FILE = Path(settings.BASE_DIR) / ".vapid.json"


def generate() -> dict:
    vapid = Vapid01()
    vapid.generate_keys()
    private_pem = vapid.private_pem().decode()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return {
        "public_key": base64.urlsafe_b64encode(public).decode().rstrip("="),
        "private_pem": private_pem,
    }


def ensure_dev_keys() -> dict:
    if DEV_KEYS_FILE.exists():
        return json.loads(DEV_KEYS_FILE.read_text())
    keys = generate()
    DEV_KEYS_FILE.write_text(json.dumps(keys))
    return keys


@lru_cache(maxsize=1)
def keys() -> dict:
    """Keys from the environment, or the development file. Raises ProviderNotConfigured."""
    if settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY:
        return {
            "public_key": settings.VAPID_PUBLIC_KEY,
            "private_pem": settings.VAPID_PRIVATE_KEY.replace("\\n", "\n"),
        }
    if settings.PROVIDERS_CONSOLE:
        return ensure_dev_keys()
    raise ProviderNotConfigured("web push")


def public_key() -> str:
    return keys()["public_key"]


def signer() -> Vapid01:
    return Vapid01.from_pem(keys()["private_pem"].encode())
