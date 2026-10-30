"""Switches of the ads and boosts, the house advertiser and the notification texts of the
boosts. Rows already there are never overwritten: they are edited in the admin."""

from django.db import migrations

ON = {"in_app": True, "push": True, "email": True, "whatsapp": False, "sms": False}

EVENTS = {
    "ads.boost_started": (
        "Le boost de la pro est payé : sa vitrine passe en tête.",
        "/pro/boost",
        {
            "fr": ("Ton boost est lancé", "Ta vitrine est en tête jusqu'au {{ until }}."),
            "en": ("Your boost is on", "Your showcase comes first until {{ until }}."),
            "sk": ("Tvoj boost beží", "Tvoja vizitka je na prvom mieste do {{ until }}."),
        },
    ),
    "ads.boost_ended": (
        "Le boost de la pro est terminé, avec ses chiffres.",
        "/pro/boost",
        {
            "fr": (
                "Ton boost est terminé",
                "{{ impressions }} affichages et {{ clicks }} clics. Relance-le quand tu veux.",
            ),
            "en": (
                "Your boost is over",
                "{{ impressions }} impressions and {{ clicks }} clicks. Start it again any time.",
            ),
            "sk": (
                "Tvoj boost skončil",
                "{{ impressions }} zobrazení a {{ clicks }} kliknutí. Spusti ho znova kedykoľvek.",
            ),
        },
    ),
}

FLAGS = [
    ("ads", "Publicité", "Régie publicitaire : campagnes, promos internes, AdSense (module 12)."),
    ("boosts", "Boosts des pros", "Les pros paient pour passer en tête (module 12)."),
]


def create(apps, schema_editor):
    Flag = apps.get_model("core", "FeatureFlag")
    for key, name, description in FLAGS:
        Flag.objects.get_or_create(
            key=key, defaults={"name": name, "description": description, "is_enabled": True}
        )
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, link, texts) in EVENTS.items():
        for channel, active in ON.items():
            values = {"description": description, "link": link, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)
    Advertiser = apps.get_model("ads", "Advertiser")
    Advertiser.objects.get_or_create(
        kind="house", pro=None, defaults={"name": "Solange Glow"}
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ads", "0001_initial"),
        ("core", "0004_media_documents"),
        ("notifications", "0004_contactmessage"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
