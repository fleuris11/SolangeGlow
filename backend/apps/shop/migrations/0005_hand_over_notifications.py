"""Texts of the orders paid at the hand-over (no payment tells the people, the shop does).
Rows already there are never overwritten: they are edited in the admin."""

from django.db import migrations

ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}

EVENTS = {
    "shop.order_new": (
        "Le professionnel reçoit une commande à encaisser à la remise.",
        "/pro/shop",
        {
            "fr": (
                "Nouvelle commande {{ reference }}",
                "Une commande de {{ amount }} t'attend. Le client paie à la remise.",
            ),
            "en": (
                "New order {{ reference }}",
                "An order of {{ amount }} is waiting for you. The client pays at the hand-over.",
            ),
            "sk": (
                "Nová objednávka {{ reference }}",
                "Čaká ťa objednávka za {{ amount }}. Klient platí pri odovzdaní.",
            ),
        },
    ),
    "shop.order_on_the_way": (
        "Le client apprend que sa commande est en route (paiement à la livraison).",
        "/orders",
        {
            "fr": (
                "Ta commande est en route",
                "{{ shop }} a envoyé ta commande {{ reference }}. Prépare le paiement pour la livraison.",
            ),
            "en": (
                "Your order is on its way",
                "{{ shop }} sent your order {{ reference }}. Get the payment ready for the delivery.",
            ),
            "sk": (
                "Tvoja objednávka je na ceste",
                "{{ shop }} poslal tvoju objednávku {{ reference }}. Priprav si platbu pri doručení.",
            ),
        },
    ),
    "shop.order_ready": (
        "Le client apprend que sa commande est prête à retirer (paiement au retrait).",
        "/orders",
        {
            "fr": (
                "Ta commande est prête",
                "{{ shop }} t'attend pour ta commande {{ reference }}. Tu paies sur place.",
            ),
            "en": (
                "Your order is ready",
                "{{ shop }} is waiting for you with your order {{ reference }}. You pay there.",
            ),
            "sk": (
                "Tvoja objednávka je pripravená",
                "{{ shop }} ťa čaká s objednávkou {{ reference }}. Platíš na mieste.",
            ),
        },
    ),
    "shop.order_handed_over": (
        "Le client confirme qu'il a reçu et payé sa commande.",
        "/orders",
        {
            "fr": (
                "Commande reçue",
                "{{ shop }} a noté ta commande {{ reference }} comme remise et payée. Merci !",
            ),
            "en": (
                "Order received",
                "{{ shop }} marked your order {{ reference }} as handed over and paid. Thank you!",
            ),
            "sk": (
                "Objednávka prevzatá",
                "{{ shop }} označil tvoju objednávku {{ reference }} ako odovzdanú a zaplatenú. Ďakujeme!",
            ),
        },
    ),
    "shop.order_cancelled": (
        "Une commande à payer à la remise est annulée (prévient l'autre personne).",
        "/orders",
        {
            "fr": ("Commande annulée", "La commande {{ reference }} chez {{ shop }} est annulée."),
            "en": ("Order cancelled", "The order {{ reference }} at {{ shop }} is cancelled."),
            "sk": ("Objednávka zrušená", "Objednávka {{ reference }} v {{ shop }} je zrušená."),
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
    dependencies = [("shop", "0004_hand_over_payment"), ("notifications", "0004_contactmessage")]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
