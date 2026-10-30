"""The invitation sent to a prospect (WhatsApp first, SMS otherwise), edited in the admin."""

from django.db import migrations

CHANNELS = {"whatsapp": True, "sms": True, "in_app": False, "push": False, "email": False}
TEXTS = {
    "fr": (
        "Rejoins Solange Glow",
        "Bonjour {{ name }}, crée ta vitrine gratuite sur Solange Glow : rendez-vous, "
        "boutique et paiement sécurisé. {{ link }}",
    ),
    "en": (
        "Join Solange Glow",
        "Hello {{ name }}, create your free page on Solange Glow: appointments, shop and "
        "secure payment. {{ link }}",
    ),
    "sk": (
        "Pridaj sa k Solange Glow",
        "Dobrý deň {{ name }}, vytvor si bezplatnú stránku na Solange Glow: termíny, "
        "obchod a bezpečná platba. {{ link }}",
    ),
}


def create(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for channel, active in CHANNELS.items():
        values = {
            "description": "Invitation envoyée à une pro à démarcher (prospection).",
            "link": "",
            "is_active": active,
        }
        for lang, (title, body) in TEXTS.items():
            values[f"title_{lang}"] = title
            values[f"body_{lang}"] = body
        values["title"], values["body"] = values["title_fr"], values["body_fr"]
        Template.objects.get_or_create(
            event_key="prospects.invitation", channel=channel, defaults=values
        )


class Migration(migrations.Migration):
    dependencies = [
        ("backoffice", "0001_initial"),
        ("notifications", "0004_contactmessage"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
