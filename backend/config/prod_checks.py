"""What production refuses to start with: better no site than an unsafe one."""

from __future__ import annotations

# Set to true in the environment, these would turn a development shortcut on.
FORBIDDEN_FLAGS = (
    "DJANGO_DEBUG",
    "ACCOUNTS_OTP_CONSOLE",
    "ACCOUNTS_DEV_OTP_ENDPOINT",
    "PROVIDERS_CONSOLE",
    "PAYMENTS_FAKE_ENABLED",
)
PLACEHOLDERS = ("change-me", "dev-only", "not-for-production", "insecure")
MIN_SECRET_LENGTH = 40
TRUE_VALUES = {"1", "true", "yes", "on"}


def _weak(value: str) -> bool:
    return len(value) < MIN_SECRET_LENGTH or any(word in value for word in PLACEHOLDERS)


def unsafe_settings(
    *,
    secret_key: str,
    allowed_hosts: list[str],
    site_url: str,
    internal_token: str,
    vault_key: str,
    bucket: str,
    environ: dict,
) -> list[str]:
    """Every problem found, named so that the owner can fix them all in one go."""
    problems = []
    if _weak(secret_key):
        problems.append(f"DJANGO_SECRET_KEY: at least {MIN_SECRET_LENGTH} random characters.")
    if _weak(internal_token):
        problems.append(f"INTERNAL_API_TOKEN: at least {MIN_SECRET_LENGTH} random characters.")
    if not allowed_hosts or "*" in allowed_hosts:
        problems.append("DJANGO_ALLOWED_HOSTS: the real domain names, never a star.")
    if not site_url.startswith("https://"):
        problems.append("SITE_URL: the public address, starting with https://.")
    if not vault_key:
        problems.append("IDENTITY_VAULT_KEY: required (identity documents, ADR-005).")
    if not bucket:
        problems.append("AWS_STORAGE_BUCKET_NAME: media must live on the object storage.")
    for flag in FORBIDDEN_FLAGS:
        if str(environ.get(flag, "")).strip().lower() in TRUE_VALUES:
            problems.append(f"{flag}: development only, remove it.")
    return problems
