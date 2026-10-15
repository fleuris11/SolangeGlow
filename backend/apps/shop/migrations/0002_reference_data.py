"""Product categories, the first forbidden words, the « shop » switch and the notification
texts. Rows already there are never overwritten (edited in the admin)."""

import unicodedata

from django.db import migrations

CATEGORIES = [
    ("makeup", "Maquillage", "Makeup", "Líčenie", "PaintBrush"),
    ("skincare", "Soins de la peau", "Skincare", "Starostlivosť o pleť", "Drop"),
    ("hair", "Cheveux et perruques", "Hair and wigs", "Vlasy a parochne", "HairDryer"),
    ("nails", "Ongles", "Nails", "Nechty", "HandPalm"),
    ("fragrance", "Parfums", "Fragrances", "Parfumy", "Sparkle"),
    ("fabrics", "Tissus et couture", "Fabrics and sewing", "Látky a šitie", "Scissors"),
    ("clothing", "Mode", "Fashion", "Móda", "Dress"),
    ("accessories", "Accessoires", "Accessories", "Doplnky", "Handbag"),
]

ABMED = "Dépigmentant interdit dans les cosmétiques (ABMed, Bénin)"
DRUG = "Médicament : vente réservée aux pharmacies"
LIGHTENING = "Produit éclaircissant : vérifié par l'équipe avant la mise en vente"
FAKE = "Possible contrefaçon : vérifiée par l'équipe"

# To compare with the official list of the ABMed before opening the shops.
TERMS = [
    ("hydroquinone", "block", ABMED),
    ("clobetasol", "block", ABMED),
    ("betamethasone", "block", ABMED),
    ("dexamethasone", "block", ABMED),
    ("fluocinolone", "block", ABMED),
    ("mercure", "block", ABMED),
    ("mercury", "block", ABMED),
    ("calomel", "block", ABMED),
    ("monobenzone", "block", ABMED),
    ("hydrocortisone", "review", DRUG),
    ("tretinoine", "review", DRUG),
    ("tretinoin", "review", DRUG),
    ("eclaircissant", "review", LIGHTENING),
    ("eclaircissante", "review", LIGHTENING),
    ("blanchissant", "review", LIGHTENING),
    ("blanchissante", "review", LIGHTENING),
    ("depigmentant", "review", LIGHTENING),
    ("whitening", "review", LIGHTENING),
    ("glutathion", "review", LIGHTENING),
    ("glutathione", "review", LIGHTENING),
    ("acide kojique", "review", LIGHTENING),
    ("contrefacon", "review", FAKE),
    ("replique", "review", FAKE),
]

ON = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
WITH_WHATSAPP = {**ON, "whatsapp": True}

EVENTS = {
    "shop.order_preparing": (
        "La cliente apprend que sa commande est en préparation.",
        WITH_WHATSAPP,
        {
            "fr": ("Commande en préparation", "{{ shop }} prépare ta commande {{ reference }}."),
            "en": ("Order being prepared", "{{ shop }} is preparing your order {{ reference }}."),
            "sk": ("Objednávka sa pripravuje", "{{ shop }} pripravuje tvoju objednávku {{ reference }}."),
        },
    ),
    "shop.back_in_stock": (
        "Un produit attendu est de retour en stock.",
        ON,
        {
            "fr": ("De retour en stock", "{{ product }} {{ choice }} est de nouveau disponible."),
            "en": ("Back in stock", "{{ product }} {{ choice }} is available again."),
            "sk": ("Opäť na sklade", "{{ product }} {{ choice }} je opäť k dispozícii."),
        },
    ),
    "shop.price_drop": (
        "Baisse de prix d'un produit de la liste d'envies.",
        ON,
        {
            "fr": ("Le prix baisse !", "{{ product }} passe de {{ before }} à {{ price }}."),
            "en": ("Price drop!", "{{ product }} goes from {{ before }} to {{ price }}."),
            "sk": ("Cena klesla!", "{{ product }} z {{ before }} na {{ price }}."),
        },
    ),
    "shop.product_approved": (
        "Un produit vérifié par l'équipe est en ligne.",
        ON,
        {
            "fr": ("Produit en ligne", "{{ product }} a été vérifié : il est en vente."),
            "en": ("Product online", "{{ product }} was checked: it is on sale."),
            "sk": ("Produkt je online", "{{ product }} bol skontrolovaný: je v predaji."),
        },
    ),
    "shop.product_refused": (
        "Un produit refusé par l'équipe.",
        {**ON, "email": True},
        {
            "fr": ("Produit refusé", "{{ product }} ne peut pas être vendu : {{ reason }}"),
            "en": ("Product refused", "{{ product }} cannot be sold: {{ reason }}"),
            "sk": ("Produkt zamietnutý", "{{ product }} sa nemôže predávať: {{ reason }}"),
        },
    ),
}


def _plain(text):
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def create(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    for position, (key, fr, en, sk, icon) in enumerate(CATEGORIES):
        Category.objects.get_or_create(
            key=key,
            defaults={
                "name": fr,
                "name_fr": fr,
                "name_en": en,
                "name_sk": sk,
                "icon": icon,
                "position": position,
            },
        )
    Term = apps.get_model("shop", "ForbiddenTerm")
    for term, action, reason in TERMS:
        if not Term.objects.filter(normalized=_plain(term)).exists():
            Term.objects.create(term=term, normalized=_plain(term), action=action, reason=reason)
    Flag = apps.get_model("core", "FeatureFlag")
    Flag.objects.get_or_create(
        key="shop",
        defaults={
            "name": "Boutiques des pros",
            "description": "Boutiques, panier et commandes (module 4). Couper par pays si besoin.",
            "is_enabled": True,
        },
    )
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, channels, texts) in EVENTS.items():
        link = "/pro/shop/products" if event_key.startswith("shop.product_") else "/orders"
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
        ("shop", "0001_initial"),
        ("core", "0001_initial"),
        ("notifications", "0003_notificationdelivery_sensitive"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
