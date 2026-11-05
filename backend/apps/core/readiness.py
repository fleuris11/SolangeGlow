"""What is still to connect before opening: shown as a banner on the admin home."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Level:
    BLOCKING = "blocking"  # nobody can pay in a whole country
    RECOMMENDED = "recommended"  # a promised feature stays off
    OPTIONAL = "optional"  # the platform works without it


@dataclass(frozen=True)
class Check:
    key: str
    label: object
    effect: object
    level: str
    variables: tuple[str, ...]

    @property
    def is_set(self) -> bool:
        return all(getattr(settings, name, "") for name in self.variables)


SIGN_IN = ("whatsapp", "sms", "email")
CHECKS = (
    Check(
        "payments_bj",
        _("Payments in Benin (FedaPay)"),
        _("Nobody can pay in Benin."),
        Level.BLOCKING,
        ("FEDAPAY_SECRET_KEY", "FEDAPAY_WEBHOOK_SECRET"),
    ),
    Check(
        "payments_fr",
        _("Payments in France (Stripe Connect)"),
        _("Nobody can pay in France, gifts from abroad included."),
        Level.BLOCKING,
        ("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"),
    ),
    Check(
        "whatsapp",
        _("WhatsApp Business"),
        _("No code or message goes through WhatsApp."),
        Level.RECOMMENDED,
        ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID"),
    ),
    Check(
        "sms",
        _("SMS (Twilio)"),
        _("No code or message goes through SMS."),
        Level.RECOMMENDED,
        ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"),
    ),
    Check(
        "email",
        _("E-mail (SMTP)"),
        _("No e-mail is sent."),
        Level.RECOMMENDED,
        ("EMAIL_HOST",),
    ),
    Check(
        "push",
        _("Push notifications (VAPID)"),
        _("No alert on the phones."),
        Level.RECOMMENDED,
        ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY"),
    ),
    Check(
        "livekit",
        _("Calls and lives (LiveKit)"),
        _("Calls and lives stay off."),
        Level.RECOMMENDED,
        ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"),
    ),
    Check(
        "moderation_ai",
        _("AI moderation"),
        _("Only the word lists and the rules check what is published."),
        Level.OPTIONAL,
        ("MODERATION_AI_URL",),
    ),
    Check(
        "quiz_ai",
        _("AI for the quizzes"),
        _("The team writes the quizzes by hand."),
        Level.OPTIONAL,
        ("QUIZ_AI_URL",),
    ),
    Check(
        "help_ai",
        _("AI of the help center"),
        _("The help center only suggests the answers of the FAQ."),
        Level.OPTIONAL,
        ("HELP_AI_URL",),
    ),
    Check(
        "errors",
        _("Error tracking (GlitchTip)"),
        _("Errors stay in the server logs."),
        Level.OPTIONAL,
        ("SENTRY_DSN",),
    ),
)


def missing() -> dict:
    """The banner: what is missing, the most serious first, and whether sign-in is possible."""
    order = [Level.BLOCKING, Level.RECOMMENDED, Level.OPTIONAL]
    found = sorted((c for c in CHECKS if not c.is_set), key=lambda c: order.index(c.level))
    keys = {c.key for c in found}
    return {
        "entries": [
            {
                "key": c.key,
                "label": c.label,
                "effect": c.effect,
                "level": c.level,
                "variables": ", ".join(c.variables),
            }
            for c in found
        ],
        # Codes are the only way in: without any channel nobody can sign in.
        "no_sign_in": all(key in keys for key in SIGN_IN),
        # Stand-ins without keys: said on the banner so that nobody mistakes them for real.
        "simulated": bool(settings.PROVIDERS_CONSOLE or settings.PAYMENTS_FAKE_ENABLED),
    }


def payments_switch() -> dict:
    """The banner of the free launch: online payment stays closed until the owner opens it."""
    from django.urls import reverse

    from apps.core.models import FeatureFlag
    from apps.core.selectors import payments_open

    flag = FeatureFlag.objects.filter(key="payments_closed").first()
    link = (
        reverse("admin:core_featureflag_change", args=[flag.pk])
        if flag
        else reverse("admin:core_featureflag_changelist")
    )
    return {"open": payments_open(), "link": link}
