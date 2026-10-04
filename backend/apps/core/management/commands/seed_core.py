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

# Secure payment (escrow) deadlines. Starting values, to be confirmed by the owner;
# they are edited in the admin, never in the code.
SETTINGS = [
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
    {
        "key": "escrow.ship_deadline_days",
        "country": None,
        "value_type": INT,
        "value": "3",
        "description_fr": "Jours laissés à la pro pour expédier ou remettre la commande. "
        "Passé ce délai, la cliente est remboursée automatiquement.",
        "description_en": "Days the seller has to ship or hand over the order. After "
        "that, the client is refunded automatically.",
    },
    {
        "key": "escrow.ship_deadline_days",
        "country": "FR",
        "value_type": INT,
        "value": "5",
        "description_fr": "Délai d'expédition pour les commandes en France.",
        "description_en": "Shipping deadline for orders in France.",
    },
    {
        "key": "escrow.auto_release_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours après la livraison sans code de réception ni litige, "
        "au bout desquels l'argent bloqué est versé à la pro.",
        "description_en": "Days after delivery, without receipt code or dispute, after "
        "which the held money is released to the seller.",
    },
    {
        "key": "escrow.dispute_resolution_days",
        "country": None,
        "value_type": INT,
        "value": "7",
        "description_fr": "Jours dont l'équipe dispose pour trancher un litige.",
        "description_en": "Days the team has to settle a dispute.",
    },
    {
        "key": "escrow.receipt_code_max_attempts",
        "country": None,
        "value_type": INT,
        "value": "5",
        "description_fr": "Nombre d'essais autorisés pour saisir le code de réception.",
        "description_en": "Number of attempts allowed to enter the receipt code.",
    },
]


class Command(BaseCommand):
    help = "Create countries (BJ, FR), currencies (XOF, EUR) and the first platform settings."

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
