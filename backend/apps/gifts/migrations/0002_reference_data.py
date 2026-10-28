"""The switch of the gifts, their fee (6 % paid by the giver, owner's choice of November
2026, between the 5 and 8 % of the specification) and the notification texts. Rows
already there are never overwritten: they are edited in the admin."""

from django.db import migrations

RULES = [
    {
        "kind": "buyer_protection",
        "name": "Gifts from abroad: 6 % paid by the giver",
        "purpose": "gift",
        "country": "FR",
        "currency": "EUR",
        "percent_bps": 600,
    },
]

ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}
GUEST = {**ON, "whatsapp": True, "sms": True}

EVENTS = {
    "gifts.received": (
        "La personne reçoit son cadeau (WhatsApp, sinon SMS, et son compte si elle en a un).",
        GUEST,
        {
            "fr": ("{{ from }} t'envoie un cadeau", "{{ what }}. Ouvre-le ici : {{ link }}"),
            "en": ("{{ from }} sends you a gift", "{{ what }}. Open it here: {{ link }}"),
            "sk": ("{{ from }} ti posiela darček", "{{ what }}. Otvor ho tu: {{ link }}"),
        },
    ),
    "gifts.reminder": (
        "Rappel à la personne : son cadeau n'est pas encore utilisé.",
        GUEST,
        {
            "fr": (
                "Ton cadeau t'attend",
                "{{ from }} t'a offert : {{ what }}. Valable jusqu'au {{ until }}. {{ link }}",
            ),
            "en": (
                "Your gift is waiting",
                "{{ from }} gave you: {{ what }}. Valid until {{ until }}. {{ link }}",
            ),
            "sk": (
                "Tvoj darček čaká",
                "{{ from }} ti daroval(a): {{ what }}. Platí do {{ until }}. {{ link }}",
            ),
        },
    ),
    "gifts.proof_ask": (
        "Après la prestation offerte : envoyer une photo à la personne qui a offert ?",
        GUEST,
        {
            "fr": (
                "Ton cadeau t'a plu ?",
                "Envoie une photo du résultat à {{ from }}. Rien ne part sans ton accord. {{ link }}",
            ),
            "en": (
                "Did you enjoy your gift?",
                "Send a photo of the result to {{ from }}. Nothing leaves without your yes. {{ link }}",
            ),
            "sk": (
                "Páčil sa ti darček?",
                "Pošli fotku výsledku pre {{ from }}. Nič neodíde bez tvojho súhlasu. {{ link }}",
            ),
        },
    ),
    "gifts.scheduled": (
        "Le cadeau est payé, il partira le jour choisi.",
        ON,
        {
            "fr": ("Cadeau payé", "Il partira pour {{ name }} le {{ date }}."),
            "en": ("Gift paid", "It will go to {{ name }} on {{ date }}."),
            "sk": ("Darček zaplatený", "Odíde pre {{ name }} dňa {{ date }}."),
        },
    ),
    "gifts.sent": (
        "Le cadeau est parti vers la personne.",
        ON,
        {
            "fr": ("Ton cadeau est parti", "{{ name }} a reçu son lien : {{ what }}."),
            "en": ("Your gift is on its way", "{{ name }} got her link: {{ what }}."),
            "sk": ("Tvoj darček je na ceste", "{{ name }} dostala odkaz: {{ what }}."),
        },
    ),
    "gifts.opened": (
        "La personne a ouvert son cadeau.",
        ON,
        {
            "fr": ("{{ name }} a ouvert ton cadeau", "{{ what }}"),
            "en": ("{{ name }} opened your gift", "{{ what }}"),
            "sk": ("{{ name }} otvorila tvoj darček", "{{ what }}"),
        },
    ),
    "gifts.used": (
        "La personne a utilisé son cadeau (rendez-vous, commande, achat).",
        ON,
        {
            "fr": ("{{ name }} a utilisé ton cadeau", "{{ what }}."),
            "en": ("{{ name }} used your gift", "{{ what }}."),
            "sk": ("{{ name }} použila tvoj darček", "{{ what }}."),
        },
    ),
    "gifts.proof": (
        "La personne envoie une photo du résultat (preuve de plaisir).",
        ON,
        {
            "fr": ("Une photo de {{ name }}", "Le résultat de ton cadeau. Regarde !"),
            "en": ("A photo from {{ name }}", "The result of your gift. Have a look!"),
            "sk": ("Fotka od {{ name }}", "Výsledok tvojho darčeka. Pozri sa!"),
        },
    ),
    "gifts.refunded": (
        "Le cadeau est annulé et remboursé en euros.",
        ON,
        {
            "fr": ("Cadeau annulé", "Ton cadeau pour {{ name }} est annulé, l'argent te revient."),
            "en": ("Gift cancelled", "Your gift for {{ name }} is cancelled, you get your money back."),
            "sk": ("Darček zrušený", "Tvoj darček pre {{ name }} je zrušený, peniaze sa ti vrátia."),
        },
    ),
}


def create(apps, schema_editor):
    Flag = apps.get_model("core", "FeatureFlag")
    Flag.objects.get_or_create(
        key="gifts",
        defaults={
            "name": "Offrir au pays",
            "description": "Cadeaux payés en euros, reçus et utilisés au Bénin (module 9).",
            "is_enabled": True,
        },
    )
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, channels, texts) in EVENTS.items():
        for channel, active in channels.items():
            values = {"description": description, "link": "/cadeaux", "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("gifts", "0001_initial"),
        ("core", "0004_media_documents"),
        ("notifications", "0004_contactmessage"),
        ("payments", "0010_alter_payment_purpose_alter_pricingrule_purpose"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
