"""The commission on gift cards sold online and the notification texts of the salon.
Rows already there are never overwritten."""

from django.db import migrations

RULES = [
    {
        "kind": "commission",
        "name": "Gift cards of the salons: 5 % commission",
        "purpose": "gift_card",
        "percent_bps": 500,
    },
]

ON = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
GUEST = {**ON, "whatsapp": True, "sms": True}

EVENTS = {
    "salon.gift_card_received": (
        "Une personne reçoit une carte cadeau (message WhatsApp ou SMS).",
        GUEST,
        "/",
        {
            "fr": ("Une carte cadeau pour toi !", "{{ from }} t'offre {{ amount }} chez {{ pro }}. Code : {{ code }}, valable jusqu'au {{ until }}. {{ message }}"),
            "en": ("A gift card for you!", "{{ from }} gives you {{ amount }} at {{ pro }}. Code: {{ code }}, valid until {{ until }}. {{ message }}"),
            "sk": ("Darčeková karta pre teba!", "{{ from }} ti darúva {{ amount }} v {{ pro }}. Kód: {{ code }}, platí do {{ until }}. {{ message }}"),
        },
    ),
    "salon.gift_card_bought": (
        "L'acheteuse reçoit sa carte cadeau.",
        ON,
        "/",
        {
            "fr": ("Ta carte cadeau est prête", "{{ amount }} chez {{ pro }}. Code : {{ code }}, valable jusqu'au {{ until }}."),
            "en": ("Your gift card is ready", "{{ amount }} at {{ pro }}. Code: {{ code }}, valid until {{ until }}."),
            "sk": ("Tvoja darčeková karta je pripravená", "{{ amount }} v {{ pro }}. Kód: {{ code }}, platí do {{ until }}."),
        },
    ),
    "salon.package_last_session": (
        "Il reste une séance sur le forfait de la cliente.",
        ON,
        "/appointments",
        {
            "fr": ("Plus qu'une séance", "Il te reste une séance sur ton forfait {{ package }} chez {{ pro }}."),
            "en": ("One session left", "You have one session left on your {{ package }} package at {{ pro }}."),
            "sk": ("Ostáva jedno sedenie", "Na balíku {{ package }} v {{ pro }} ti ostáva jedno sedenie."),
        },
    ),
    "salon.installment_due": (
        "Une échéance de paiement arrive.",
        ON,
        "/appointments",
        {
            "fr": ("Paiement à venir", "Ton prochain paiement pour {{ label }} est prévu le {{ date }}."),
            "en": ("Payment coming", "Your next payment for {{ label }} is due on {{ date }}."),
            "sk": ("Blíži sa platba", "Ďalšia platba za {{ label }} je splatná {{ date }}."),
        },
    ),
    "salon.stock_low": (
        "Un produit du stock est presque épuisé.",
        ON,
        "/pro/stock",
        {
            "fr": ("Bientôt en rupture", "{{ item }} : plus que {{ quantity }} {{ unit }}."),
            "en": ("Running out soon", "{{ item }}: only {{ quantity }} {{ unit }} left."),
            "sk": ("Čoskoro dôjde", "{{ item }}: ostáva len {{ quantity }} {{ unit }}."),
        },
    ),
}


def create(apps, schema_editor):
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, channels, link, texts) in EVENTS.items():
        for channel, active in channels.items():
            values = {"description": description, "link": link, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("salon", "0001_initial"),
        ("notifications", "0004_contactmessage"),
        ("payments", "0008_glowpro_purposes"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
