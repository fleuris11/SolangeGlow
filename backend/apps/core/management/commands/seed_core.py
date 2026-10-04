"""Create the reference data the platform needs to start.

Safe to run several times: existing rows are never overwritten, so values edited in
the admin are kept.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Country, Currency, PlatformSetting

CURRENCIES = [
    {
        "code": "XOF",
        "symbol": "FCFA",
        "decimal_places": 0,
        "name_fr": "Franc CFA (BCEAO)",
        "name_en": "West African CFA franc",
        "name_sk": "Západoafrický frank CFA",
    },
    {
        "code": "EUR",
        "symbol": "€",
        "decimal_places": 2,
        "name_fr": "Euro",
        "name_en": "Euro",
        "name_sk": "Euro",
    },
]

COUNTRIES = [
    {
        "code": "BJ",
        "phone_prefix": "+229",
        "currency": "XOF",
        "default_language": "fr",
        "timezone": "Africa/Porto-Novo",
        "name_fr": "Bénin",
        "name_en": "Benin",
        "name_sk": "Benin",
    },
    {
        "code": "FR",
        "phone_prefix": "+33",
        "currency": "EUR",
        "default_language": "fr",
        "timezone": "Europe/Paris",
        "name_fr": "France",
        "name_en": "France",
        "name_sk": "Francúzsko",
    },
]

INT = PlatformSetting.ValueType.INTEGER

# Secure payment (escrow) deadlines, from module 5 of the specification (v2).
# They are edited in the admin, never in the code.
SETTINGS = [
    {
        "key": "escrow.ship_deadline_days",
        "country": None,
        "value_type": INT,
        "value": "3",
        "description_fr": "Jours laissés à la vendeuse pour expédier ou remettre la commande. "
        "Passé ce délai, la commande est annulée et la cliente remboursée.",
        "description_en": "Days the seller has to ship or hand over the order. After "
        "that, the order is cancelled and the client refunded.",
    },
    {
        "key": "escrow.auto_release_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours après un suivi transporteur « livré » sans code de réception : "
        "relances à la cliente, puis argent versé à la vendeuse si elle ne dit rien.",
        "description_en": "Days after a carrier 'delivered' status without receipt code: "
        "the client is reminded, then the money is released to the seller.",
    },
    {
        "key": "escrow.auto_dispute_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours après la date de livraison prévue, sans code ni preuve de "
        "livraison, au bout desquels un litige s'ouvre automatiquement.",
        "description_en": "Days after the expected delivery date, without code or proof of "
        "delivery, after which a dispute opens automatically.",
    },
    {
        "key": "escrow.dispute_response_hours",
        "country": None,
        "value_type": INT,
        "value": "48",
        "description_fr": "Heures laissées à chaque partie pour répondre et déposer ses "
        "preuves dans un litige.",
        "description_en": "Hours each party has to answer and upload evidence in a dispute.",
    },
    {
        "key": "escrow.receipt_code_max_attempts",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Nombre d'essais autorisés pour saisir le code de réception.",
        "description_en": "Number of attempts allowed to enter the receipt code.",
    },
    {
        "key": "escrow.payment_timeout_minutes",
        "country": None,
        "value_type": INT,
        "value": "30",
        "description_fr": "Minutes laissées à la cliente pour finaliser un paiement "
        "avant l'annulation de la commande.",
        "description_en": "Minutes the client has to complete a payment before the "
        "order is cancelled.",
    },
]


STR = PlatformSetting.ValueType.STRING
JSON = PlatformSetting.ValueType.JSON

# Sign-in with one-time codes and request limits.
SETTINGS += [
    {
        "key": "otp.code_ttl_seconds",
        "country": None,
        "value_type": INT,
        "value": "600",
        "description_fr": "Durée de validité d'un code de connexion, en secondes.",
        "description_en": "How long a sign-in code stays valid, in seconds.",
    },
    {
        "key": "otp.max_attempts",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Essais autorisés pour taper un code avant d'en demander un nouveau.",
        "description_en": "Attempts allowed to type a code before asking for a new one.",
    },
    {
        "key": "otp.resend_cooldown_seconds",
        "country": None,
        "value_type": INT,
        "value": "60",
        "description_fr": "Secondes à attendre avant de pouvoir redemander un code.",
        "description_en": "Seconds to wait before a new code can be asked.",
    },
    {
        "key": "otp.max_requests_per_destination_per_hour",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Codes envoyés au maximum par heure à un même numéro ou e-mail.",
        "description_en": "Maximum codes sent per hour to the same number or e-mail.",
    },
    {
        "key": "otp.max_requests_per_ip_per_hour",
        "country": None,
        "value_type": INT,
        "value": "20",
        "description_fr": "Codes demandés au maximum par heure depuis une même adresse IP.",
        "description_en": "Maximum codes asked per hour from the same IP address.",
    },
    {
        "key": "otp.phone_channels",
        "country": None,
        "value_type": JSON,
        "value": '["whatsapp", "sms"]',
        "description_fr": "Canaux d'envoi des codes vers un téléphone, dans l'ordre : le "
        "suivant sert de secours. Valeurs : whatsapp, sms.",
        "description_en": "Channels used to send codes to a phone, in order: the next one is "
        "the fallback. Values: whatsapp, sms.",
    },
    {
        "key": "otp.email_channels",
        "country": None,
        "value_type": JSON,
        "value": '["email"]',
        "description_fr": "Canaux d'envoi des codes vers une adresse e-mail.",
        "description_en": "Channels used to send codes to an e-mail address.",
    },
    {
        "key": "accounts.avatar_max_bytes",
        "country": None,
        "value_type": INT,
        "value": str(5 * 1024 * 1024),
        "description_fr": "Taille maximale d'une photo de profil, en octets.",
        "description_en": "Maximum size of a profile photo, in bytes.",
    },
    {
        "key": "throttle.auth",
        "country": None,
        "value_type": STR,
        "value": "30/minute",
        "description_fr": "Limite de connexions par adresse IP (format : 30/minute).",
        "description_en": "Sign-in limit per IP address (format: 30/minute).",
    },
    {
        "key": "throttle.otp_request",
        "country": None,
        "value_type": STR,
        "value": "10/minute",
        "description_fr": "Limite de demandes de code par adresse IP (format : 10/minute).",
        "description_en": "Code request limit per IP address (format: 10/minute).",
    },
    {
        "key": "throttle.guest",
        "country": None,
        "value_type": STR,
        "value": "10/hour",
        "description_fr": "Limite de créations d'identité invitée par adresse IP.",
        "description_en": "Guest identity creation limit per IP address.",
    },
    {
        "key": "throttle.profile",
        "country": None,
        "value_type": STR,
        "value": "60/minute",
        "description_fr": "Limite de modifications du profil par adresse IP.",
        "description_en": "Profile update limit per IP address.",
    },
]


class Command(BaseCommand):
    help = "Create countries (BJ, FR), currencies (XOF, EUR) and the platform settings."

    @transaction.atomic
    def handle(self, *args, **options):
        created = {"currencies": 0, "countries": 0, "settings": 0}

        currencies = {}
        for data in CURRENCIES:
            data = dict(data)
            code = data.pop("code")
            data["name"] = data["name_fr"]
            currencies[code], was_created = Currency.objects.get_or_create(code=code, defaults=data)
            created["currencies"] += was_created

        countries = {}
        for data in COUNTRIES:
            data = dict(data)
            code = data.pop("code")
            data["default_currency"] = currencies[data.pop("currency")]
            data["name"] = data["name_fr"]
            countries[code], was_created = Country.objects.get_or_create(code=code, defaults=data)
            created["countries"] += was_created

        for data in SETTINGS:
            data = dict(data)
            key = data.pop("key")
            country_code = data.pop("country")
            country = countries[country_code] if country_code else None
            data["description"] = data["description_fr"]
            _, was_created = PlatformSetting.objects.get_or_create(
                key=key, country=country, defaults=data
            )
            created["settings"] += was_created

        self.stdout.write(
            self.style.SUCCESS(
                "seed_core: {currencies} currencies, {countries} countries, "
                "{settings} settings created.".format(**created)
            )
        )
