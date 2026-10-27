"""Switches of the calls and of the sales lives, notification texts of the calls and the
lives, the lives of the month in Glow Pro Premium (10). Rows already there are never
overwritten: they are edited in the admin."""

from django.db import migrations

FLAGS = [
    ("calls", "Appels audio et vidéo", "Appels dans la messagerie et appel à trois des litiges."),
    ("live_sales", "Ventes en live", "Les boutiques vérifiées vendent en direct (module 4)."),
]

QUICK = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}

EVENTS = {
    "messaging.call_incoming": (
        "Quelqu'un appelle dans la messagerie (sans numéro).",
        "/messages",
        QUICK,
        {
            "fr": ("{{ name }} t'appelle", "{{ kind }} dans Solange Glow. Touche pour répondre."),
            "en": ("{{ name }} is calling you", "{{ kind }} in Solange Glow. Tap to answer."),
            "sk": ("{{ name }} ti volá", "{{ kind }} v Solange Glow. Ťukni a odpovedz."),
        },
    ),
    "messaging.call_missed": (
        "Un appel n'a pas eu de réponse.",
        "/messages",
        QUICK,
        {
            "fr": ("Appel manqué", "{{ name }} a essayé de t'appeler."),
            "en": ("Missed call", "{{ name }} tried to call you."),
            "sk": ("Zmeškaný hovor", "{{ name }} sa ti pokúsila zavolať."),
        },
    ),
    "academy.live_on_air": (
        "Le live de formation commence : les inscrites peuvent entrer.",
        "/academie/lives",
        QUICK,
        {
            "fr": ("C'est parti, le live commence", "« {{ live }} » est en direct. Entre maintenant."),
            "en": ("The live is starting", "« {{ live }} » is on air. Come in now."),
            "sk": ("Live začína", "« {{ live }} » je naživo. Vstúp teraz."),
        },
    ),
    "academy.live_replay": (
        "Le replay du live est prêt (pour les inscrites).",
        "/academie/lives",
        ON,
        {
            "fr": ("Le replay est prêt", "Revois « {{ live }} » quand tu veux."),
            "en": ("The replay is ready", "Watch « {{ live }} » again whenever you want."),
            "sk": ("Záznam je pripravený", "Pozri si « {{ live }} » znova, kedy chceš."),
        },
    ),
    "shop.live_on_air": (
        "Une boutique suivie commence une vente en live.",
        "/",
        QUICK,
        {
            "fr": ("{{ shop }} est en live", "« {{ live }} » : viens voir et acheter en direct."),
            "en": ("{{ shop }} is live", "« {{ live }} »: come and shop live."),
            "sk": ("{{ shop }} je naživo", "« {{ live }} »: príď nakupovať naživo."),
        },
    ),
}


def create(apps, schema_editor):
    Flag = apps.get_model("core", "FeatureFlag")
    for key, name, description in FLAGS:
        Flag.objects.get_or_create(
            key=key, defaults={"name": name, "description": description, "is_enabled": True}
        )
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, link, channels, texts) in EVENTS.items():
        for channel, active in channels.items():
            values = {"description": description, "link": link, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)
    Plan = apps.get_model("glowpro", "Plan")
    premium = Plan.objects.filter(key="premium").first()
    if premium is not None and "lives_per_month" not in (premium.limits or {}):
        premium.limits = {**(premium.limits or {}), "lives_per_month": 10}
        premium.save(update_fields=["limits"])


class Migration(migrations.Migration):
    dependencies = [
        ("live", "0001_initial"),
        ("core", "0004_media_documents"),
        ("notifications", "0004_contactmessage"),
        ("glowpro", "0002_reference_data"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
