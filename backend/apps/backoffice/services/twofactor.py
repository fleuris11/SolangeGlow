"""Two-factor authentication of the team (TOTP, RFC 6238): a 6-digit code that changes every
30 seconds in an authenticator app (Google Authenticator, Authy…), plus backup codes.

Written here (HMAC-SHA1, a few lines) rather than with a new library: nothing else to
install, nothing else to keep up to date.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.core import crypto
from apps.core.audit.services import record
from apps.core.selectors import get_setting

from ..models import RecoveryCode, StaffDevice

STEP = 30
DIGITS = 6
SESSION_KEY = "backoffice_2fa_at"


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def current_step(now: float | None = None) -> int:
    return int((now if now is not None else time.time()) // STEP)


def provisioning_uri(secret: str, account: str) -> str:
    issuer = "Solange Glow"
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}"
        f"?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"
    )


def secret_of(device: StaffDevice) -> str:
    return crypto.decrypt(device.secret) or ""


def device_of(user) -> StaffDevice:
    """Her device, created (not confirmed) the first time she opens the set-up page."""
    found = StaffDevice.objects.filter(user=user).first()
    if found is None:
        found = StaffDevice.objects.create(user=user, secret=crypto.encrypt(new_secret()))
    return found


def _attempts_left(user) -> bool:
    most = int(get_setting("backoffice.two_factor_attempts", default=5))
    return int(cache.get(f"2fa:tries:{user.pk}") or 0) < most


def _failed(user) -> None:
    key = f"2fa:tries:{user.pk}"
    minutes = int(get_setting("backoffice.two_factor_lock_minutes", default=15))
    if not cache.add(key, 1, minutes * 60):
        cache.incr(key)


@transaction.atomic
def verify(user, code: str, *, now: float | None = None) -> bool:
    """The code of the app (one step before or after is accepted); never twice the same."""
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    device = StaffDevice.objects.select_for_update().filter(user=user).first()
    if device is None or not _attempts_left(user) or len(code) != DIGITS:
        _failed(user)
        return False
    secret = secret_of(device)
    step = current_step(now)
    for candidate in (step - 1, step, step + 1):
        if candidate > device.last_step and hmac.compare_digest(code_at(secret, candidate), code):
            device.last_step = candidate
            fields = ["last_step", "updated_at"]
            if device.confirmed_at is None:
                device.confirmed_at = timezone.now()
                fields.append("confirmed_at")
                record("backoffice.two_factor_enabled", device, actor=user)
            device.save(update_fields=fields)
            cache.delete(f"2fa:tries:{user.pk}")
            return True
    _failed(user)
    return False


def new_recovery_codes(user, count: int = 10) -> list[str]:
    """Ten new backup codes, shown once; the old ones stop working."""
    RecoveryCode.objects.filter(user=user).delete()
    codes = [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(count)]
    RecoveryCode.objects.bulk_create(
        RecoveryCode(user=user, code_hash=make_password(code)) for code in codes
    )
    return codes


@transaction.atomic
def use_recovery_code(user, code: str) -> bool:
    code = (code or "").strip().lower()
    if not _attempts_left(user):
        return False
    for row in RecoveryCode.objects.select_for_update().filter(user=user, used_at__isnull=True):
        if check_password(code, row.code_hash):
            row.used_at = timezone.now()
            row.save(update_fields=["used_at", "updated_at"])
            record("backoffice.recovery_code_used", row, actor=user)
            return True
    _failed(user)
    return False


def is_set_up(user) -> bool:
    return StaffDevice.objects.filter(user=user, confirmed_at__isnull=False).exists()


def mark_verified(request) -> None:
    request.session[SESSION_KEY] = timezone.now().timestamp()


def is_verified(request) -> bool:
    at = request.session.get(SESSION_KEY)
    hours = float(get_setting("backoffice.two_factor_hours", default=12))
    return bool(at) and timezone.now().timestamp() - float(at) < hours * 3600


@transaction.atomic
def reset(user, *, actor) -> None:
    """Lost phone: the member sets up her app again at the next sign-in."""
    StaffDevice.objects.filter(user=user).delete()
    RecoveryCode.objects.filter(user=user).delete()
    record("backoffice.two_factor_reset", user, actor=actor)
