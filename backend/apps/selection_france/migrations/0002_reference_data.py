"""Categories, pricing rules of the Selection (no buyer protection: the price is final), the
« selection » switch for Benin and the notification texts. Existing rows are never changed."""

from django.db import migrations

# key, fr, en, sk, air restricted, own parameters (empty: the defaults of the settings)
CATEGORIES = [
    ("makeup", "Maquillage", "Makeup", "Líčenie", False, {}),
    ("skincare", "Soins", "Skincare", "Starostlivosť", False, {}),
    ("hair", "Cheveux", "Hair", "Vlasy", False, {}),
    ("accessories", "Accessoires", "Accessories", "Doplnky", False, {"customs_bps": 1500}),
    ("fashion", "Mode", "Fashion", "Móda", False, {"customs_bps": 2500}),
    ("fragrance", "Parfums", "Fragrances", "Parfumy", True, {"margin_bps": 3000}),
    ("aerosols", "Aérosols", "Aerosols", "Aerosóly", True, {}),
]

RULES = [
    {
        "kind": "buyer_protection",
        "name": "France Selection: no buyer protection (final price)",
        "purpose": "selection",
        "percent_bps": 0,
    },
    {
        "kind": "commission",
        "name": "France Selection: no commission (the platform sells)",
        "purpose": "selection",
        "percent_bps": 0,
    },
]

ON = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
WHATSAPP = {**ON, "whatsapp": True}
TEAM = {**ON, "email": True}

EVENTS = {
    "selection.order_to_place": (
        "Équipe : une commande Sélection France est à passer chez le marchand.",
        TEAM,
        {
            "fr": ("Commande à passer ({{ reference }})", "{{ product }} : passe la commande chez le marchand."),
            "en": ("Order to place ({{ reference }})", "{{ product }}: place the order at the merchant."),
            "sk": ("Objednávka na zadanie ({{ reference }})", "{{ product }}: zadaj objednávku u obchodníka."),
        },
    ),
    "selection.request_new": (
        "Équipe : nouvelle demande spéciale à chiffrer.",
        TEAM,
        {
            "fr": ("Nouvelle demande spéciale", "{{ name }} cherche un produit : envoie-lui un devis."),
            "en": ("New special request", "{{ name }} looks for a product: send a quote."),
            "sk": ("Nová špeciálna požiadavka", "{{ name }} hľadá produkt: pošli ponuku."),
        },
    ),
    "selection.ordered": (
        "La commande est passée chez le marchand.",
        ON,
        {
            "fr": ("Commande passée ({{ reference }})", "{{ product }} est commandé en France."),
            "en": ("Order placed ({{ reference }})", "{{ product }} is ordered in France."),
            "sk": ("Objednávka zadaná ({{ reference }})", "{{ product }} je objednaný vo Francúzsku."),
        },
    ),
    "selection.received": (
        "Le produit est arrivé chez nous en France.",
        ON,
        {
            "fr": ("Reçu en France ({{ reference }})", "{{ product }} est arrivé : il part au prochain envoi."),
            "en": ("Received in France ({{ reference }})", "{{ product }} arrived: it leaves with the next shipment."),
            "sk": ("Prijaté vo Francúzsku ({{ reference }})", "{{ product }} dorazil: odchádza s ďalšou zásielkou."),
        },
    ),
    "selection.arrived": (
        "Le colis attend la cliente au point de retrait.",
        WHATSAPP,
        {
            "fr": ("Ton colis est arrivé ({{ reference }})", "{{ product }} t'attend à {{ place }}. Donne ton code de réception sur place."),
            "en": ("Your parcel arrived ({{ reference }})", "{{ product }} waits for you at {{ place }}. Give your receipt code there."),
            "sk": ("Tvoj balík dorazil ({{ reference }})", "{{ product }} ťa čaká v {{ place }}. Na mieste daj kód prevzatia."),
        },
    ),
    "selection.quote_ready": (
        "Le devis d'une demande spéciale est prêt.",
        WHATSAPP,
        {
            "fr": ("Ton devis est prêt", "{{ product }} : regarde le prix et paie si ça te va."),
            "en": ("Your quote is ready", "{{ product }}: see the price and pay if it suits you."),
            "sk": ("Tvoja ponuka je pripravená", "{{ product }}: pozri cenu a zaplať, ak ti vyhovuje."),
        },
    ),
    "selection.request_refused": (
        "Une demande spéciale n'est pas possible.",
        ON,
        {
            "fr": ("Demande pas possible", "Nous ne pouvons pas te l'envoyer. {{ answer }}"),
            "en": ("Request not possible", "We cannot send it to you. {{ answer }}"),
            "sk": ("Požiadavka nie je možná", "Nemôžeme ti to poslať. {{ answer }}"),
        },
    ),
    "selection.group_reached": (
        "Précommande groupée : l'objectif est atteint.",
        ON,
        {
            "fr": ("Objectif atteint !", "La précommande de {{ product }} part : on passe la commande."),
            "en": ("Goal reached!", "The pre-order of {{ product }} goes ahead: we place the order."),
            "sk": ("Cieľ dosiahnutý!", "Predobjednávka {{ product }} pokračuje: zadávame objednávku."),
        },
    ),
    "selection.group_failed": (
        "Précommande groupée : objectif pas atteint, remboursement.",
        WHATSAPP,
        {
            "fr": ("Précommande annulée", "L'objectif de {{ product }} n'est pas atteint : tu es remboursée."),
            "en": ("Pre-order cancelled", "The goal of {{ product }} was not reached: you are refunded."),
            "sk": ("Predobjednávka zrušená", "Cieľ {{ product }} sa nedosiahol: peniaze sa ti vrátia."),
        },
    ),
}


def create(apps, schema_editor):
    Category = apps.get_model("selection_france", "SelectionCategory")
    for position, (key, fr, en, sk, restricted, params) in enumerate(CATEGORIES):
        Category.objects.get_or_create(
            key=key,
            defaults={
                "name": fr,
                "name_fr": fr,
                "name_en": en,
                "name_sk": sk,
                "position": position,
                "air_restricted": restricted,
                **params,
            },
        )
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)
    Flag = apps.get_model("core", "FeatureFlag")
    flag, created = Flag.objects.get_or_create(
        key="selection",
        defaults={
            "name": "Sélection France",
            "description": "Produits achetés en France et envoyés au Bénin (module 6).",
            "is_enabled": True,
        },
    )
    if created:
        Country = apps.get_model("core", "Country")
        flag.countries.add(*Country.objects.filter(code="BJ"))
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, channels, texts) in EVENTS.items():
        link = "/selection/requests" if "quote" in event_key or "request" in event_key else "/selection/orders"
        for channel, active in channels.items():
            values = {"description": description, "link": link, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"] = values["title_fr"]
            values["body"] = values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("selection_france", "0001_initial"),
        ("payments", "0007_selection_purpose"),
        ("core", "0001_initial"),
        ("notifications", "0003_notificationdelivery_sensitive"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
