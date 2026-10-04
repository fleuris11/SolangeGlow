"""Account business rules: one-time codes, sign-in, profile, guests, deletion.

Views stay thin and call these functions. Limits (code lifetime, attempts, rates,
channel order) come from platform settings, never from the code.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

import phonenumbers
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.core.choices import Role
from apps.core.models import Country
from apps.core.selectors import get_setting
from apps.pros.models import ProProfile, Trade

from . import errors
from .models import GuestIdentity, LoginEvent, OtpChallenge, SignupChannel, User
from .otp.base import OtpDeliveryError, OtpMessage
from .otp.registry import get_sender

logger = logging.getLogger("solangeglow.accounts")

LANGUAGE_CODES = {code for code, _ in settings.LANGUAGES}


# --- Helpers -----------------------------------------------------------------------


def _hmac(*parts: str) -> str:
    """Keyed hash: codes and destinations are never stored or compared in clear."""
    message = "|".join(parts).encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def destination_hash(value: str) -> str:
    return _hmac("destination", value)


@dataclass(frozen=True)
class Destination:
    kind: str  # "phone" | "email"
    value: str  # E.164 phone or lowercase e-mail
    country_code: str = ""


def parse_destination(*, phone: str | None = None, email: str | None = None) -> Destination:
    """Normalise what the person typed. Exactly one of phone or e-mail is expected."""
    phone = (phone or "").strip()
    email = (email or "").strip().lower()
    if bool(phone) == bool(email):
        raise errors.InvalidDestination()

    if email:
        try:
            validate_email(email)
        except ValidationError as exc:
            raise errors.InvalidDestination() from exc
        return Destination(OtpChallenge.DestinationKind.EMAIL, email)

    try:
        number = phonenumbers.parse(phone, settings.PHONENUMBER_DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise errors.InvalidDestination() from exc
    if not phonenumbers.is_valid_number(number):
        raise errors.InvalidDestination()
    return Destination(
        OtpChallenge.DestinationKind.PHONE,
        phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164),
        phonenumbers.region_code_for_number(number) or "",
    )


def _clean_locale(locale: str | None) -> str:
    code = (locale or "").split("-")[0].lower()
    return code if code in LANGUAGE_CODES else settings.LANGUAGE_CODE


def record_login(
    *,
    user: User | None,
    method: str,
    success: bool,
    channel: str = "",
    reason: str = "",
    ip: str | None = None,
    user_agent: str = "",
) -> LoginEvent:
    return LoginEvent.objects.create(
        user=user,
        method=method,
        channel=channel,
        success=success,
        failure_reason=reason,
        ip_address=ip or None,
        user_agent=(user_agent or "")[:255],
    )


# --- One-time codes ------------------------------------------------------------------


@dataclass(frozen=True)
class CodeRequest:
    challenge_id: str
    channel: str
    resend_after: int
    expires_in: int


def request_code(
    *,
    phone: str | None = None,
    email: str | None = None,
    ip: str | None = None,
    locale: str | None = None,
) -> CodeRequest:
    """Create and send a one-time code.

    The answer is the same whether an account exists or not: sign-up and sign-in share
    this path, so nobody can find out who is registered.
    """
    destination = parse_destination(phone=phone, email=email)
    country = destination.country_code or None
    now = timezone.now()
    dest_hash = destination_hash(destination.value)
    ip_hash = _hmac("ip", ip) if ip else ""

    cooldown = int(get_setting("otp.resend_cooldown_seconds", country=country, default=60))
    last = OtpChallenge.objects.filter(destination_hash=dest_hash).order_by("-created_at").first()
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < cooldown:
            raise errors.ResendTooSoon(details={"retry_after": int(cooldown - elapsed) + 1})

    hour_ago = now - timedelta(hours=1)
    per_destination = int(
        get_setting("otp.max_requests_per_destination_per_hour", country=country, default=5)
    )
    if (
        OtpChallenge.objects.filter(destination_hash=dest_hash, created_at__gte=hour_ago).count()
        >= per_destination
    ):
        raise errors.TooManyRequests(details={"retry_after": 3600})
    if ip_hash:
        per_ip = int(get_setting("otp.max_requests_per_ip_per_hour", country=country, default=20))
        if OtpChallenge.objects.filter(ip_hash=ip_hash, created_at__gte=hour_ago).count() >= per_ip:
            raise errors.TooManyRequests(details={"retry_after": 3600})

    ttl = int(get_setting("otp.code_ttl_seconds", country=country, default=600))
    code = f"{secrets.randbelow(10**6):06d}"
    challenge = OtpChallenge(
        destination_kind=destination.kind,
        destination=destination.value,
        destination_hash=dest_hash,
        country_code=destination.country_code,
        expires_at=now + timedelta(seconds=ttl),
        max_attempts=int(get_setting("otp.max_attempts", country=country, default=5)),
        ip_hash=ip_hash,
    )
    challenge.code_hash = _hmac("code", str(challenge.id), code)

    setting_key = (
        "otp.phone_channels"
        if destination.kind == OtpChallenge.DestinationKind.PHONE
        else "otp.email_channels"
    )
    default_channels = ["whatsapp", "sms"] if destination.kind == "phone" else ["email"]
    channels = list(get_setting(setting_key, country=country, default=default_channels))
    if settings.ACCOUNTS_OTP_CONSOLE and "console" not in channels:
        channels.append("console")

    message = OtpMessage(destination.value, code, _clean_locale(locale), max(1, ttl // 60))
    for channel in channels:
        sender = get_sender(channel)
        if sender is None or sender.destination_kind not in (destination.kind, "any"):
            continue
        if not sender.is_available():
            continue
        try:
            sender.send(message)
        except OtpDeliveryError as exc:
            logger.warning("One-time code not delivered on %s: %s", channel, exc)
            continue
        challenge.channel = channel
        challenge.save()
        return CodeRequest(str(challenge.id), channel, cooldown, ttl)

    # Counted for rate limits even though nothing went out.
    challenge.save()
    raise errors.DeliveryFailed()


@dataclass(frozen=True)
class SignInResult:
    user: User
    created: bool


def verify_code(
    *,
    challenge_id: str,
    code: str,
    ip: str | None = None,
    user_agent: str = "",
    locale: str | None = None,
    guest_id: str | None = None,
) -> SignInResult:
    """Check a code. On success, sign the person in, creating the account if needed."""
    code = (code or "").strip()
    failure: errors.DomainError | None = None

    with transaction.atomic():
        try:
            challenge = OtpChallenge.objects.select_for_update().get(pk=challenge_id)
        except (OtpChallenge.DoesNotExist, ValidationError, ValueError) as exc:
            raise errors.ChallengeNotFound() from exc

        if challenge.verified_at:
            raise errors.ChallengeNotFound()
        if challenge.attempts >= challenge.max_attempts:
            raise errors.TooManyAttempts()
        if challenge.expires_at <= timezone.now():
            raise errors.CodeExpired()

        expected = _hmac("code", str(challenge.id), code)
        if not hmac.compare_digest(expected, challenge.code_hash):
            # Saved before raising: the wrong attempt must count.
            challenge.attempts += 1
            challenge.save(update_fields=["attempts", "updated_at"])
            left = challenge.max_attempts - challenge.attempts
            failure = (
                errors.TooManyAttempts()
                if left <= 0
                else errors.InvalidCode(details={"attempts_left": left})
            )
        else:
            challenge.verified_at = timezone.now()
            challenge.save(update_fields=["verified_at", "updated_at"])

    if failure:
        record_login(
            user=None,
            method=LoginEvent.Method.OTP,
            channel=challenge.channel,
            success=False,
            reason=failure.code,
            ip=ip,
            user_agent=user_agent,
        )
        raise failure

    user, created = _get_or_create_user(challenge, locale)
    if not user.is_active:
        record_login(
            user=user,
            method=LoginEvent.Method.OTP,
            channel=challenge.channel,
            success=False,
            reason=errors.AccountSuspended.code,
            ip=ip,
            user_agent=user_agent,
        )
        raise errors.AccountSuspended()

    if guest_id:
        attach_guest(user, guest_id)
    record_login(
        user=user,
        method=LoginEvent.Method.OTP,
        channel=challenge.channel,
        success=True,
        ip=ip,
        user_agent=user_agent,
    )
    return SignInResult(user, created)


def _get_or_create_user(challenge: OtpChallenge, locale: str | None) -> tuple[User, bool]:
    now = timezone.now()
    is_phone = challenge.destination_kind == OtpChallenge.DestinationKind.PHONE
    lookup = (
        {"phone": challenge.destination} if is_phone else {"email__iexact": challenge.destination}
    )
    user = User.objects.filter(**lookup).first()
    created = False

    if user is None:
        country = Country.objects.filter(code=challenge.country_code).first() if is_phone else None
        user = User.objects.create_user(
            phone=challenge.destination if is_phone else None,
            email=None if is_phone else challenge.destination,
            signup_channel=SignupChannel.PHONE if is_phone else SignupChannel.EMAIL,
            preferred_language=_clean_locale(locale),
            country=country,
            preferred_currency=country.default_currency if country else None,
        )
        created = True

    field = "phone_verified_at" if is_phone else "email_verified_at"
    if getattr(user, field) is None:
        setattr(user, field, now)
        user.save(update_fields=[field, "updated_at"])
    return user, created


# --- Password (optional) -------------------------------------------------------------


def login_with_password(
    *, identifier: str, password: str, ip: str | None = None, user_agent: str = ""
) -> User:
    user = authenticate(username=identifier, password=password)
    if user is None:
        # No lookup of who it was: the journal must not help guessing accounts.
        record_login(
            user=None,
            method=LoginEvent.Method.PASSWORD,
            success=False,
            reason=errors.InvalidCredentials.code,
            ip=ip,
            user_agent=user_agent,
        )
        raise errors.InvalidCredentials()
    record_login(
        user=user, method=LoginEvent.Method.PASSWORD, success=True, ip=ip, user_agent=user_agent
    )
    return user


def set_password(user: User, password: str) -> None:
    """Optional password: the person can always sign in again with a code."""
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])


# --- Sessions ------------------------------------------------------------------------


def revoke_all_tokens(user: User) -> None:
    """Sign out on every device: refresh tokens are blacklisted, access tokens refused."""
    user.tokens_revoked_at = timezone.now()
    user.save(update_fields=["tokens_revoked_at", "updated_at"])
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def suspend(user: User) -> None:
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    revoke_all_tokens(user)


def reactivate(user: User) -> None:
    if user.deleted_at:
        return
    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])


# --- Profile -------------------------------------------------------------------------


def complete_onboarding(
    user: User,
    *,
    mode: str,
    trade_keys: list[str] | None = None,
    language: str | None = None,
    city: str = "",
) -> User:
    """End of the welcome screens: client or pro (with trades), language, city."""
    if mode == Role.PRO:
        if Role.PRO not in user.roles:
            user.roles = [*user.roles, Role.PRO]
        profile, _ = ProProfile.objects.get_or_create(user=user)
        trades = Trade.objects.filter(is_active=True, key__in=trade_keys or [])
        profile.trades.set(trades)
    if language:
        user.preferred_language = _clean_locale(language)
    if city:
        user.city = city.strip()[:80]
    if user.onboarded_at is None:
        user.onboarded_at = timezone.now()
    user.save()
    return user


AVATAR_SIZE = 512
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}


def save_avatar(user: User, uploaded) -> User:
    """Check the photo, re-encode it and drop every metadata (the GPS position must never leak)."""
    max_bytes = int(get_setting("accounts.avatar_max_bytes", default=5 * 1024 * 1024))
    if uploaded.size > max_bytes:
        raise errors.ImageTooLarge(
            errors.ImageTooLarge.message % {"size": max_bytes // (1024 * 1024)}
        )

    try:
        probe = Image.open(uploaded)
        image_format = probe.format
        probe.verify()
        uploaded.seek(0)
        image = Image.open(uploaded)
        image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise errors.InvalidImage() from exc
    if image_format not in ACCEPTED_FORMATS:
        raise errors.InvalidImage()

    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, (AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=82)  # no exif/icc passed: metadata are dropped

    if user.avatar:
        user.avatar.delete(save=False)
    user.avatar.save("avatar.webp", ContentFile(buffer.getvalue()), save=False)
    user.save(update_fields=["avatar", "updated_at"])
    return user


def remove_avatar(user: User) -> User:
    if user.avatar:
        user.avatar.delete(save=False)
        user.avatar = ""
        user.save(update_fields=["avatar", "updated_at"])
    return user


@transaction.atomic
def delete_account(user: User) -> None:
    """Delete on request: personal data are erased at once, the account is closed."""
    revoke_all_tokens(user)
    if user.avatar:
        user.avatar.delete(save=False)
    GuestIdentity.objects.filter(user=user).delete()
    ProProfile.objects.filter(user=user).delete()
    user.email = f"deleted-{user.pk.hex}@deleted.invalid"
    user.phone = None
    user.first_name = ""
    user.last_name = ""
    user.city = ""
    user.avatar = ""
    user.is_active = False
    user.deleted_at = timezone.now()
    user.set_unusable_password()
    user.save()


# --- Guests --------------------------------------------------------------------------


def create_guest(*, first_name: str, phone: str) -> GuestIdentity:
    destination = parse_destination(phone=phone)
    return GuestIdentity.objects.create(
        first_name=first_name.strip()[:150], phone=destination.value
    )


def attach_guest(user: User, guest_id: str) -> int:
    """Guest becomes a client: what she did as a guest now belongs to her account."""
    try:
        return GuestIdentity.objects.filter(pk=guest_id, user__isnull=True).update(
            user=user, converted_at=timezone.now()
        )
    except (ValidationError, ValueError):
        return 0
