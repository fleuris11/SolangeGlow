from django.db import migrations

# Default texts (fr, en, sk), editable afterwards in the admin; never overwritten.
EVENTS = {
    "pros.client_arrived": {
        "description": "« Je suis devant » : la cliente est à la porte de la pro.",
        "link": "/pro",
        "texts": {
            "fr": ("{{ name }} est devant chez toi", "Ta cliente est arrivée. Va lui ouvrir !"),
            "en": ("{{ name }} is outside", "Your client has arrived. Go and open the door!"),
            "sk": ("{{ name }} je pred dverami", "Tvoja klientka prišla. Choď jej otvoriť!"),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "pros.published": {
        "description": "Première publication de la vitrine d'une pro.",
        "link": "/pro",
        "texts": {
            "fr": ("Ta vitrine est en ligne", "Partage ton lien {{ link }} et imprime ton QR code."),
            "en": ("Your showcase is online", "Share your link {{ link }} and print your QR code."),
            "sk": ("Tvoja vitrína je online", "Zdieľaj svoj odkaz {{ link }} a vytlač si QR kód."),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "pros.verification_approved": {
        "description": "Pièce d'identité validée : badge « Pro vérifiée ».",
        "link": "/pro",
        "texts": {
            "fr": ("Tu es une pro vérifiée", "Ton badge « Pro vérifiée » s'affiche sur ta vitrine."),
            "en": ("You are a verified pro", "Your « Verified pro » badge shows on your showcase."),
            "sk": ("Si overená profesionálka", "Odznak « Overená » sa zobrazuje na tvojej vitríne."),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "pros.verification_rejected": {
        "description": "Pièce d'identité refusée, avec la raison.",
        "link": "/pro",
        "texts": {
            "fr": ("Vérification refusée", "Raison : {{ reason }}. Tu peux renvoyer tes documents."),
            "en": ("Verification refused", "Reason: {{ reason }}. You can send your documents again."),
            "sk": ("Overenie zamietnuté", "Dôvod: {{ reason }}. Dokumenty môžeš poslať znova."),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "pros.suspended": {
        "description": "Vitrine suspendue par l'équipe, avec la raison.",
        "link": "/pro",
        "texts": {
            "fr": ("Ta vitrine est suspendue", "Raison : {{ reason }}. Écris au support pour en parler."),
            "en": ("Your showcase is suspended", "Reason: {{ reason }}. Write to support to talk about it."),
            "sk": ("Tvoja vitrína je pozastavená", "Dôvod: {{ reason }}. Napíš podpore."),
        },
        "channels": {"in_app": True, "email": True, "push": False, "whatsapp": False, "sms": False},
    },
}


def create_templates(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, event in EVENTS.items():
        for channel, active in event["channels"].items():
            values = {"description": event["description"], "link": event["link"], "is_active": active}
            for lang, (title, body) in event["texts"].items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"] = values["title_fr"]
            values["body"] = values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("pros", "0003_showcase_services_hours_portfolio_verification"),
        ("notifications", "0002_seed_templates"),
    ]

    operations = [migrations.RunPython(create_templates, migrations.RunPython.noop)]
