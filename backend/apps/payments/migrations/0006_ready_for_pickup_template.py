from django.db import migrations

CHANNELS = {"in_app": True, "email": False, "push": True, "whatsapp": True, "sms": False}

TEXTS = {
    "fr": (
        "Ta commande t'attend ({{ reference }})",
        "Elle est prête : passe la chercher et donne ton code de réception sur place.",
    ),
    "en": (
        "Your order is waiting ({{ reference }})",
        "It is ready: pick it up and give your receipt code there.",
    ),
    "sk": (
        "Tvoja objednávka čaká ({{ reference }})",
        "Je pripravená: vyzdvihni si ju a na mieste daj kód prevzatia.",
    ),
}


def create(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for channel, active in CHANNELS.items():
        values = {
            "description": "Commande prête à retirer chez la vendeuse.",
            "link": "/payments",
            "is_active": active,
        }
        for lang, (title, body) in TEXTS.items():
            values[f"title_{lang}"] = title
            values[f"body_{lang}"] = body
        values["title"] = values["title_fr"]
        values["body"] = values["body_fr"]
        Template.objects.get_or_create(
            event_key="payments.ready_for_pickup", channel=channel, defaults=values
        )


class Migration(migrations.Migration):
    dependencies = [("payments", "0005_payment_groups")]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
