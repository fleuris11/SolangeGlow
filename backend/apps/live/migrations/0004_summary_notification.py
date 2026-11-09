"""The figures of a live, sent to its host when it ends (in the app, on the phone and by e-mail).
Rows already there are never overwritten: they are edited in the admin."""

from django.db import migrations

ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}

EVENTS = {
    "live.summary": (
        "Bilan envoyé au professionnel à la fin de son live.",
        "/pro/lives",
        {
            "fr": (
                "Ton live est terminé",
                "« {{ live }} » : {{ total }} personnes sont venues, {{ peak }} en même temps au plus fort, {{ comments }} commentaires.",
            ),
            "en": (
                "Your live has ended",
                "« {{ live }} »: {{ total }} people came, {{ peak }} at the same time at its peak, {{ comments }} comments.",
            ),
            "sk": (
                "Tvoj live sa skončil",
                "« {{ live }} »: prišlo {{ total }} ľudí, naraz najviac {{ peak }}, {{ comments }} komentárov.",
            ),
        },
    ),
}


def create(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, link, texts) in EVENTS.items():
        for channel, active in ON.items():
            values = {"description": description, "link": link, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [("live", "0003_comments_and_blocks"), ("notifications", "0004_contactmessage")]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
