from django.db import migrations

# Default texts (fr, en, sk). Editable afterwards in the admin; never overwritten.
# WhatsApp and SMS templates are created inactive: they cost money and need provider setup.
EVENTS = {
    "account.welcome": {
        "description": "Après la création du compte.",
        "link": "/",
        "texts": {
            "fr": ("Bienvenue sur Solange Glow !", "Ton compte est prêt. Trouve ta pro près de chez toi."),
            "en": ("Welcome to Solange Glow!", "Your account is ready. Find your pro near you."),
            "sk": ("Vitaj v Solange Glow!", "Tvoj účet je pripravený. Nájdi si profesionálku nablízku."),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "account.contact_changed": {
        "description": "Après un changement de numéro ou d'e-mail.",
        "link": "/me",
        "texts": {
            "fr": (
                "Ton numéro ou ton e-mail a changé",
                "Nouveau contact : {{ contact }}. Si ce n'est pas toi, écris-nous tout de suite.",
            ),
            "en": (
                "Your number or e-mail changed",
                "New contact: {{ contact }}. If this was not you, write to us at once.",
            ),
            "sk": (
                "Tvoje číslo alebo e-mail sa zmenil",
                "Nový kontakt: {{ contact }}. Ak si to nebola ty, hneď nám napíš.",
            ),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "account.deletion_scheduled": {
        "description": "Quand la personne demande la suppression de son compte.",
        "link": "/auth",
        "texts": {
            "fr": (
                "Ton compte sera supprimé",
                "Ton compte sera effacé le {{ date }}. Reconnecte-toi avant cette date pour le garder.",
            ),
            "en": (
                "Your account will be deleted",
                "Your account will be erased on {{ date }}. Sign in before that date to keep it.",
            ),
            "sk": (
                "Tvoj účet bude zmazaný",
                "Účet sa vymaže {{ date }}. Ak ho chceš ponechať, prihlás sa pred týmto dátumom.",
            ),
        },
        "channels": {"in_app": False, "email": True, "push": False, "whatsapp": False, "sms": False},
    },
    "account.deletion_cancelled": {
        "description": "Quand la personne se reconnecte pendant le délai de grâce.",
        "link": "/me",
        "texts": {
            "fr": ("Ton compte est gardé", "Tu t'es reconnectée : ton compte ne sera pas supprimé."),
            "en": ("Your account is kept", "You signed in again: your account will not be deleted."),
            "sk": ("Tvoj účet zostáva", "Znova si sa prihlásila: účet sa nezmaže."),
        },
        "channels": {"in_app": True, "email": True, "push": False, "whatsapp": False, "sms": False},
    },
    "system.test": {
        "description": "Bouton « Envoyer un test » de la page Notifications.",
        "link": "/notifications",
        "texts": {
            "fr": ("Test réussi", "Tes alertes Solange Glow arrivent bien sur cet appareil."),
            "en": ("Test passed", "Your Solange Glow alerts reach this device."),
            "sk": ("Test prebehol", "Upozornenia Solange Glow prichádzajú na toto zariadenie."),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
}


def create_templates(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, event in EVENTS.items():
        for channel, active in event["channels"].items():
            values = {
                "description": event["description"],
                "link": event["link"],
                "is_active": active,
            }
            for lang, (title, body) in event["texts"].items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"] = values["title_fr"]
            values["body"] = values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]

    operations = [migrations.RunPython(create_templates, migrations.RunPython.noop)]
