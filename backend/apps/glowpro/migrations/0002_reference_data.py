"""The free plan and Premium (prices in Benin and France), the payment rules of the
subscription and the notification texts. Rows already there are never overwritten."""

from django.db import migrations

FREE_FEATURES = []
PREMIUM_FEATURES = [
    "extra_staff",
    "client_file",
    "stock",
    "dashboard_full",
    "campaigns",
    "widget",
    "einvoice",
]

PLANS = [
    {
        "key": "free",
        "is_default": True,
        "position": 0,
        "trial_days": 0,
        "features": FREE_FEATURES,
        "limits": {"staff": 2, "campaigns_per_month": 0},
        "name": ("Gratuit", "Free", "Zadarmo"),
        "description": (
            "Agenda, réservation en ligne, rappels, liste d'attente, acomptes, fiches clientes, "
            "cartes cadeaux, encaissement, factures. Jusqu'à 2 personnes en plus de toi.",
            "Agenda, online booking, reminders, waiting list, deposits, client files, gift "
            "cards, payments at the salon, invoices. Up to 2 people besides you.",
            "Kalendár, online rezervácie, pripomienky, čakacia listina, zálohy, karty "
            "klientok, darčekové karty, platby v salóne, faktúry. Do 2 osôb okrem teba.",
        ),
    },
    {
        "key": "premium",
        "is_default": False,
        "position": 1,
        "trial_days": 30,
        "features": PREMIUM_FEATURES,
        "limits": {"campaigns_per_month": 4},
        "name": ("Premium", "Premium", "Premium"),
        "description": (
            "Tout le gratuit, plus : équipe sans limite, forfaits et paiements en plusieurs "
            "fois, stocks avec scan, tableau de bord complet, campagnes, widget sur ton site.",
            "Everything free, plus: unlimited team, packages and payments in several times, "
            "stock with scanning, complete dashboard, campaigns, widget on your website.",
            "Všetko zadarmo a navyše: tím bez obmedzenia, balíky a platby na splátky, sklad so "
            "skenovaním, úplný prehľad, kampane, widget na tvojom webe.",
        ),
    },
]

PRICES = [("premium", "BJ", "XOF", 9_900), ("premium", "FR", "EUR", 2_900)]

RULES = [
    {
        "kind": "buyer_protection",
        "name": "Glow Pro subscription: no buyer protection",
        "purpose": "subscription",
        "percent_bps": 0,
    },
    {
        "kind": "commission",
        "name": "Glow Pro subscription: no commission (the platform sells)",
        "purpose": "subscription",
        "percent_bps": 0,
    },
]

ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}
LINK = "/pro/plan"

EVENTS = {
    "glowpro.trial_started": (
        "La pro commence son essai gratuit de Premium.",
        {
            "fr": ("Ton essai {{ plan }} commence", "{{ days }} jours pour tout essayer. Rien à payer d'ici là."),
            "en": ("Your {{ plan }} trial starts", "{{ days }} days to try everything. Nothing to pay until then."),
            "sk": ("Tvoja skúšobná verzia {{ plan }} začína", "{{ days }} dní na vyskúšanie všetkého. Dovtedy nič neplatíš."),
        },
    ),
    "glowpro.trial_ending": (
        "L'essai gratuit se termine bientôt.",
        {
            "fr": ("Ton essai se termine le {{ until }}", "Pour garder {{ plan }}, choisis « Payer le mois » dans « Mon offre »."),
            "en": ("Your trial ends on {{ until }}", "To keep {{ plan }}, choose « Pay the month » in « My plan »."),
            "sk": ("Tvoja skúšobná verzia končí {{ until }}", "Ak si chceš ponechať {{ plan }}, zvoľ « Zaplatiť mesiac » v « Môj plán »."),
        },
    ),
    "glowpro.renewal_due": (
        "Le mois suivant de l'abonnement est à payer.",
        {
            "fr": ("Ton mois {{ plan }} est à payer", "Ton abonnement se termine le {{ until }}. Paie le mois suivant dans « Mon offre »."),
            "en": ("Your {{ plan }} month is due", "Your subscription ends on {{ until }}. Pay the next month in « My plan »."),
            "sk": ("Mesiac {{ plan }} na zaplatenie", "Predplatné končí {{ until }}. Zaplať ďalší mesiac v « Môj plán »."),
        },
    ),
    "glowpro.paid": (
        "Le paiement de l'abonnement est reçu.",
        {
            "fr": ("Merci ! {{ plan }} jusqu'au {{ until }}", "Ta facture est dans « Mon offre »."),
            "en": ("Thank you! {{ plan }} until {{ until }}", "Your invoice is in « My plan »."),
            "sk": ("Ďakujeme! {{ plan }} do {{ until }}", "Faktúru nájdeš v « Môj plán »."),
        },
    ),
    "glowpro.past_due": (
        "Le mois n'est pas payé : quelques jours de grâce.",
        {
            "fr": ("Ton mois n'est pas payé", "Tu gardes Premium encore {{ days }} jours. Paie dans « Mon offre » pour ne rien perdre."),
            "en": ("Your month is not paid", "You keep Premium for {{ days }} more days. Pay in « My plan » to lose nothing."),
            "sk": ("Mesiac nie je zaplatený", "Premium ti ostáva ešte {{ days }} dní. Zaplať v « Môj plán »."),
        },
    ),
    "glowpro.ended": (
        "La pro repasse à l'offre gratuite.",
        {
            "fr": ("Tu es repassée à l'offre gratuite", "Rien n'est supprimé. Les personnes en trop de ton équipe sont en pause."),
            "en": ("You are back on the free plan", "Nothing is deleted. Extra people of your team are paused."),
            "sk": ("Vrátila si sa k bezplatnému plánu", "Nič sa nevymazalo. Nadpočetné osoby tímu sú pozastavené."),
        },
    ),
}


def create(apps, schema_editor):
    Plan = apps.get_model("glowpro", "Plan")
    PlanPrice = apps.get_model("glowpro", "PlanPrice")
    Country = apps.get_model("core", "Country")
    for data in PLANS:
        names, descriptions = data["name"], data["description"]
        values = {k: v for k, v in data.items() if k not in ("key", "name", "description")}
        for lang, name, description in zip(("fr", "en", "sk"), names, descriptions, strict=True):
            values[f"name_{lang}"] = name
            values[f"description_{lang}"] = description
        values["name"], values["description"] = names[0], descriptions[0]
        Plan.objects.get_or_create(key=data["key"], defaults=values)
    for key, code, currency, amount in PRICES:
        country = Country.objects.filter(code=code).first()
        if country is not None:
            PlanPrice.objects.get_or_create(
                plan=Plan.objects.get(key=key),
                country=country,
                defaults={"currency": currency, "amount_minor": amount},
            )
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, texts) in EVENTS.items():
        for channel, active in ON.items():
            values = {"description": description, "link": LINK, "is_active": active}
            for lang, (title, body) in texts.items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"], values["body"] = values["title_fr"], values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("glowpro", "0001_initial"),
        ("core", "0003_alter_featureflag_roles"),
        ("notifications", "0004_contactmessage"),
        ("payments", "0008_glowpro_purposes"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
