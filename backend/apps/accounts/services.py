"""Account business rules: one-time codes, sign-in, contact change, profile, age,
guests, deletion with grace period.

Views stay thin and call these functions. Limits (code lifetime, attempts, rates,
channel order, ages, grace period) come from platform settings, never from the code.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

import phonenumbers
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.core import crypto
from apps.core.audit.services import record as audit
from apps.core.choices import Role
from apps.core.media.services import create_asset, delete_asset
from apps.core.models import Country
from apps.core.selectors import get_setting
from apps.notifications.services import notify
from apps.pros.models import ProProfile, Trade

from . import errors, selectors
from .models import GuestIdentity, LoginEvent, OtpChallenge, SignupChannel, User
from .otp.base import OtpDeliveryError, OtpMessage
from .otp.registry import get_sender

logger = logging.getLogger("solangeglow.accounts")

LANGUAGE_CODES = {code for code, _ in settings.LANGUAGES}
Purpose = OtpChallenge.Purpose


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


def mask(destination: str) -> str:
    if "@" in destination:
        name, _, domain = destination.partition("@")
        return f"{name[:2]}***@{domain}"
    return f"{destination[:4]} *** {destination[-2:]}"


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


def _planned_channels(destination: Destination) -> list[str]:
    """Channels to try, in order, keeping only those that are configured."""
    country = destination.country_code or None
    if destination.kind == OtpChallenge.DestinationKind.PHONE:
        wanted = get_setting("otp.phone_channels", country=country, default=["whatsapp", "sms"])
    else:
        wanted = get_setting("otp.email_channels", country=country, default=["email"])
    channels = []
    for channel in [*wanted, "console"]:
        sender = get_sender(channel)
        if sender is None or sender.destination_kind not in (destination.kind, "any"):
            continue
        if sender.is_available() and channel not in channels:
            channels.append(channel)
    return channels


def request_code(
    *,
    phone: str | None = None,
    email: str | None = None,
    ip: str | None = None,
    locale: str | None = None,
    purpose: str = Purpose.SIGN_IN,
    user: User | None = None,
) -> CodeRequest:
    """Create a one-time code and schedule its sending (Celery).

    For sign-in, the answer is the same whether an account exists or not: sign-up and
    sign-in share this path, so nobody can find out who is registered.
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

    channels = _planned_channels(destination)
    if not channels:
        raise errors.DeliveryFailed()

    ttl = int(get_setting("otp.code_ttl_seconds", country=country, default=600))
    code = f"{secrets.randbelow(10**6):06d}"
    challenge = OtpChallenge(
        destination_kind=destination.kind,
        destination=destination.value,
        destination_hash=dest_hash,
        country_code=destination.country_code,
        purpose=purpose,
        user=user,
        expires_at=now + timedelta(seconds=ttl),
        max_attempts=int(get_setting("otp.max_attempts", country=country, default=5)),
        ip_hash=ip_hash,
        planned_channels=channels,
        code_encrypted=crypto.encrypt(f"{_clean_locale(locale)}|{code}"),
    )
    challenge.code_hash = _hmac("code", str(challenge.id), code)
    challenge.save()

    from .tasks import send_otp_code

    transaction.on_commit(lambda: send_otp_code.delay(str(challenge.pk)))
    return CodeRequest(str(challenge.id), channels[0], cooldown, ttl)


class CodeNotSentYet(Exception):
    """Every channel failed this time: the task tries again later."""


def send_challenge(challenge_id: str) -> str:
    """Body of the sending task: tries each planned channel in order (fallback)."""
    challenge = OtpChallenge.objects.filter(pk=challenge_id).first()
    if challenge is None or challenge.sent_at or challenge.verified_at:
        return "done"
    if challenge.expires_at <= timezone.now() or not challenge.code_encrypted:
        return "expired"
    secret = crypto.decrypt(challenge.code_encrypted) or ""
    locale, _, code = secret.partition("|")
    ttl_minutes = max(1, int((challenge.expires_at - challenge.created_at).total_seconds() // 60))
    message = OtpMessage(challenge.destination, code, locale, ttl_minutes)

    for channel in challenge.planned_channels:
        sender = get_sender(channel)
        if sender is None or not sender.is_available():
            continue
        try:
            sender.send(message)
        except OtpDeliveryError as exc:
            logger.warning("One-time code not delivered on %s: %s", channel, exc)
            continue
        challenge.channel = channel
        challenge.sent_at = timezone.now()
        challenge.code_encrypted = ""  # nothing to keep once sent
        challenge.save(update_fields=["channel", "sent_at", "code_encrypted", "updated_at"])
        return channel
    raise CodeNotSentYet(challenge_id)


def mark_delivery_failed(challenge_id: str) -> None:
    OtpChallenge.objects.filter(pk=challenge_id, sent_at__isnull=True).update(
        delivery_failed_at=timezone.now(), code_encrypted="", updated_at=timezone.now()
    )


def _check_code(challenge_id: str, code: str, purpose: str, *, user: User | None = None):
    """Returns the verified challenge, or (failure, challenge) when the code is wrong."""
    code = (code or "").strip()
    failure: errors.DomainError | None = None
    with transaction.atomic():
        try:
            challenge = OtpChallenge.objects.select_for_update().get(pk=challenge_id)
        except (OtpChallenge.DoesNotExist, ValidationError, ValueError) as exc:
            raise errors.ChallengeNotFound() from exc
        if challenge.purpose != purpose or (user is not None and challenge.user_id != user.pk):
            raise errors.ChallengeNotFound()
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
            challenge.code_encrypted = ""
            challenge.save(update_fields=["verified_at", "code_encrypted", "updated_at"])
    return challenge, failure


@dataclass(frozen=True)
class SignInResult:
    user: User
    created: bool
    deletion_cancelled: bool = False


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
    challenge, failure = _check_code(challenge_id, code, Purpose.SIGN_IN)
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
    if created:
        transaction.on_commit(lambda: notify(user, "account.welcome"))
    return SignInResult(user, created, deletion_cancelled=cancel_deletion(user))


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
) -> SignInResult:
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
    return SignInResult(user, False, deletion_cancelled=cancel_deletion(user))


def set_password(user: User, password: str) -> None:
    """Optional password: the person can always sign in again with a code."""
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    audit("account.password_set", user, actor=user)


# --- Change of number or e-mail ------------------------------------------------------


def request_contact_change(
    user: User,
    *,
    phone: str | None = None,
    email: str | None = None,
    ip: str | None = None,
    locale: str | None = None,
) -> CodeRequest:
    """Sends a code to the NEW number or e-mail: proving she can receive it."""
    destination = parse_destination(phone=phone, email=email)
    is_phone = destination.kind == OtpChallenge.DestinationKind.PHONE
    current = str(user.phone) if is_phone and user.phone else (user.email or "")
    if destination.value == current:
        raise errors.SameContact()
    taken = (
        User.objects.filter(phone=destination.value)
        if is_phone
        else User.objects.filter(email__iexact=destination.value)
    )
    if taken.exclude(pk=user.pk).exists():
        raise errors.ContactTaken()
    return request_code(
        phone=destination.value if is_phone else None,
        email=None if is_phone else destination.value,
        ip=ip,
        locale=locale or user.preferred_language,
        purpose=Purpose.CHANGE_CONTACT,
        user=user,
    )


def confirm_contact_change(user: User, *, challenge_id: str, code: str) -> User:
    challenge, failure = _check_code(challenge_id, code, Purpose.CHANGE_CONTACT, user=user)
    if failure:
        raise failure
    is_phone = challenge.destination_kind == OtpChallenge.DestinationKind.PHONE
    field = "phone" if is_phone else "email"
    before = {field: mask(str(getattr(user, field) or "")) or None}
    with transaction.atomic():
        if is_phone:
            if User.objects.filter(phone=challenge.destination).exclude(pk=user.pk).exists():
                raise errors.ContactTaken()
            user.phone = challenge.destination
            user.phone_verified_at = timezone.now()
        else:
            if (
                User.objects.filter(email__iexact=challenge.destination)
                .exclude(pk=user.pk)
                .exists()
            ):
                raise errors.ContactTaken()
            user.email = challenge.destination
            user.email_verified_at = timezone.now()
        user.save()
        audit(
            "account.contact_changed",
            user,
            actor=user,
            before=before,
            after={field: mask(challenge.destination)},
        )
    transaction.on_commit(
        lambda: notify(user, "account.contact_changed", {"contact": mask(challenge.destination)})
    )
    return user


# --- Sessions ------------------------------------------------------------------------


def revoke_all_tokens(user: User) -> None:
    """Sign out on every device: refresh tokens are blacklisted, access tokens refused."""
    user.tokens_revoked_at = timezone.now()
    user.save(update_fields=["tokens_revoked_at", "updated_at"])
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    audit("account.sessions_revoked", user)


def suspend(user: User, *, actor: User | None = None) -> None:
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    revoke_all_tokens(user)
    audit("account.suspended", user, actor=actor)


def reactivate(user: User, *, actor: User | None = None) -> None:
    if user.deleted_at:
        return
    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])
    audit("account.reactivated", user, actor=actor)


# --- Profile -------------------------------------------------------------------------


def complete_onboarding(
    user: User,
    *,
    mode: str,
    birth_date: datetime.date,
    trade_keys: list[str] | None = None,
    language: str | None = None,
    city: str = "",
) -> User:
    """End of the welcome screens: client or pro (with trades), birth date, language, city."""
    country = user.country.code if user.country_id else None
    minimum = int(get_setting("accounts.minimum_age", country=country, default=16))
    if birth_date > timezone.localdate() or selectors.age_on(birth_date) > 120:
        raise errors.InvalidBirthDate()
    if selectors.age_on(birth_date) < minimum:
        raise errors.TooYoung(errors.TooYoung.message % {"age": minimum})

    user.birth_date = birth_date
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


def set_photo(user: User, uploaded) -> User:
    """New profile photo: processed in the background (sizes, no metadata, blur preview)."""
    previous = user.photo
    user.photo = create_asset(owner=user, uploaded=uploaded, purpose="avatar", kind="image")
    user.save(update_fields=["photo", "updated_at"])
    if previous is not None:
        transaction.on_commit(lambda: delete_asset(previous))
    return user


def remove_photo(user: User) -> User:
    previous = user.photo
    if previous is not None:
        user.photo = None
        user.save(update_fields=["photo", "updated_at"])
        transaction.on_commit(lambda: delete_asset(previous))
    return user


# --- Deletion with grace period ------------------------------------------------------


def request_deletion(user: User) -> datetime.datetime:
    """The account is closed now and erased after the grace period, unless she comes back."""
    grace = int(get_setting("accounts.deletion_grace_days", default=30))
    user.deletion_requested_at = timezone.now()
    user.save(update_fields=["deletion_requested_at", "updated_at"])
    due = user.deletion_requested_at + timedelta(days=grace)
    audit("account.deletion_requested", user, metadata={"erase_after": due})
    notify(user, "account.deletion_scheduled", {"date": due.date()})
    revoke_all_tokens(user)
    return due


def cancel_deletion(user: User) -> bool:
    """Signing in again during the grace period keeps the account. True if cancelled."""
    if user.deletion_requested_at is None or user.deleted_at is not None:
        return False
    user.deletion_requested_at = None
    user.save(update_fields=["deletion_requested_at", "updated_at"])
    audit("account.deletion_cancelled", user, actor=user)
    transaction.on_commit(lambda: notify(user, "account.deletion_cancelled"))
    return True


@transaction.atomic
def anonymize_account(user: User) -> None:
    """Personal data are erased; the account row stays for history (orders, journal)."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
    photo = user.photo
    GuestIdentity.objects.filter(user=user).delete()
    ProProfile.objects.filter(user=user).delete()
    user.email = f"deleted-{user.pk.hex}@deleted.invalid"
    user.phone = None
    user.first_name = ""
    user.last_name = ""
    user.city = ""
    user.birth_date = None
    user.photo = None
    user.is_active = False
    user.deleted_at = timezone.now()
    user.tokens_revoked_at = timezone.now()
    user.set_unusable_password()
    user.save()
    if photo is not None:
        transaction.on_commit(lambda: delete_asset(photo))
    audit("account.anonymized", user, actor=None)


def purge_due_deletions() -> int:
    """Daily task: erase the accounts whose grace period is over."""
    grace = int(get_setting("accounts.deletion_grace_days", default=30))
    limit = timezone.now() - timedelta(days=grace)
    due = User.objects.filter(deletion_requested_at__lte=limit, deleted_at__isnull=True)
    count = 0
    for user in due:
        anonymize_account(user)
        count += 1
    return count


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
