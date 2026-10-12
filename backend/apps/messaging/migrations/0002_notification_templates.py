from django.db import migrations

# Default texts (fr, en, sk), editable afterwards in the admin; never overwritten.
# Sent only when the person is not in the app, a little after the first message, grouped.
EVENTS = {
    "messaging.new_messages": {
        "description": "Nouveaux messages non lus (regroupés).",
        "link": "/messages",
        "texts": {
            "fr": ("{{ name }} t'a écrit", "Messages non lus : {{ count }}. Réponds dans l'appli."),
            "en": ("{{ name }} wrote to you", "Unread messages: {{ count }}. Answer in the app."),
            "sk": ("{{ name }} ti napísala", "Neprečítané správy: {{ count }}. Odpovedz v aplikácii."),
        },
        "channels": {"in_app": False, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "messaging.request": {
        "description": "Une personne inconnue souhaite écrire (demande de message).",
        "link": "/messages?box=requests",
        "texts": {
            "fr": ("Demande de message de {{ name }}", "Accepte-la pour lui répondre, ou refuse-la."),
            "en": ("Message request from {{ name }}", "Accept it to answer, or decline it."),
            "sk": ("Žiadosť o správu od {{ name }}", "Prijmi ju a odpovedz, alebo ju odmietni."),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
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
        ("messaging", "0001_initial"),
        ("notifications", "0002_seed_templates"),
    ]

    operations = [migrations.RunPython(create_templates, migrations.RunPython.noop)]
