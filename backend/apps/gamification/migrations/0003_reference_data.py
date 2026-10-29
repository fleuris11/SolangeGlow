"""Switches of the games, the first wheel prizes and rewards, the calendar of the coming
celebrations and the notification texts. Rows already there are never overwritten: they
are edited in the admin."""

import datetime

from django.db import migrations

ON = {"in_app": True, "push": True, "email": False, "whatsapp": False, "sms": False}

EVENTS = {
    "glow.level_up": (
        "La cliente passe au niveau supérieur (Star, Icône).",
        "/points",
        {
            "fr": ("Nouveau niveau : {{ level }}", "Bravo ! Tu es {{ level }}. Découvre tes avantages."),
            "en": ("New level: {{ level }}", "Well done! You are {{ level }}. See your advantages."),
            "sk": ("Nová úroveň: {{ level }}", "Bravo! Si {{ level }}. Pozri si svoje výhody."),
        },
    ),
    "glow.pro_level_up": (
        "La pro passe au niveau supérieur (Confirmée, Top Pro).",
        "/pro",
        {
            "fr": (
                "Nouveau niveau : {{ level }}",
                "Ton travail est reconnu. Ton badge s'affiche sur ta vitrine.",
            ),
            "en": ("New level: {{ level }}", "Your work is recognised. Your badge is on your page."),
            "sk": ("Nová úroveň: {{ level }}", "Tvoja práca je ocenená. Odznak je na tvojej stránke."),
        },
    ),
    "glow.poll_result": (
        "« Aide-moi à choisir » : le vote de la cliente est terminé.",
        "/choisir",
        {
            "fr": ("Le vote est terminé", "A : {{ a }} %, B : {{ b }} % ({{ total }} votes)."),
            "en": ("The vote is over", "A: {{ a }} %, B: {{ b }} % ({{ total }} votes)."),
            "sk": ("Hlasovanie skončilo", "A: {{ a }} %, B: {{ b }} % ({{ total }} hlasov)."),
        },
    ),
    "glow.challenge_won": (
        "La gagnante du défi photo de la semaine.",
        "/defi",
        {
            "fr": (
                "Tu as gagné le défi !",
                "« {{ theme }} » : {{ votes }} votes. Ta photo est sur l'accueil.",
            ),
            "en": ("You won the challenge!", "« {{ theme }} »: {{ votes }} votes. Your photo is on the home page."),
            "sk": ("Vyhrala si výzvu!", "« {{ theme }} »: {{ votes }} hlasov. Tvoja fotka je na úvode."),
        },
    ),
    "glow.routine_reminder": (
        "Rappel de la routine beauté, à l'heure choisie.",
        "/routine",
        {
            "fr": ("Ta routine du {{ moment }}", "Quelques minutes pour toi. Coche tes étapes."),
            "en": ("Your {{ moment }} routine", "A few minutes for you. Tick your steps."),
            "sk": ("Tvoja rutina ({{ moment }})", "Pár minút pre seba. Odškrtni si kroky."),
        },
    ),
    "glow.celebration": (
        "Rappel avant une grande occasion du calendrier des fêtes.",
        "/fetes",
        {
            "fr": ("{{ name }} dans {{ days }} jours", "{{ message }} Trouve ta pro et tes produits."),
            "en": ("{{ name }} in {{ days }} days", "{{ message }} Find your pro and your products."),
            "sk": ("{{ name }} o {{ days }} dní", "{{ message }} Nájdi si profesionálku a produkty."),
        },
    ),
}

FLAGS = [
    ("games", "Côté ludique", "Glow Points, série, quiz, défis, « Aide-moi à choisir » (module 10)."),
    ("wheel", "Roue Glow", "Un tour gratuit par jour, jamais payant, sans achat (module 10)."),
]

# label (fr, en, sk), kind, points, discount, weight, per day, countries
PRIZES = [
    (("5 points", "5 points", "5 bodov"), "points", 5, 0, 30, None, []),
    (("10 points", "10 points", "10 bodov"), "points", 10, 0, 25, None, []),
    (("25 points", "25 points", "25 bodov"), "points", 25, 0, 12, None, []),
    (("50 points", "50 points", "50 bodov"), "points", 50, 0, 5, None, []),
    (("-500 FCFA Sélection", "-500 FCFA Selection", "-500 FCFA Selection"), "amount_off", 0, 500, 8, 50, ["BJ"]),
    (("-1 000 FCFA Sélection", "-1,000 FCFA Selection", "-1 000 FCFA Selection"), "amount_off", 0, 1000, 3, 10, ["BJ"]),
    (("Express offert", "Free express", "Expres zadarmo"), "express", 0, 0, 2, 5, ["BJ"]),
    (("À demain !", "See you tomorrow!", "Zajtra znova!"), "nothing", 0, 0, 15, None, []),
]

# title (fr, en, sk), kind, cost, discount, level, countries
REWARDS = [
    (
        ("-1 000 FCFA sur la Sélection France", "1,000 FCFA off the France Selection", "-1 000 FCFA na France Selection"),
        "amount_off", 500, 1000, "glow", ["BJ"],
    ),
    (
        ("Express offert (Sélection France)", "Free express shipping (France Selection)", "Expres zadarmo (France Selection)"),
        "express", 800, 0, "glow", ["BJ"],
    ),
    (
        ("-2 500 FCFA sur la Sélection France", "2,500 FCFA off the France Selection", "-2 500 FCFA na France Selection"),
        "amount_off", 1200, 2500, "star", ["BJ"],
    ),
]

D = datetime.date
# name (fr, en, sk), message (fr, en, sk), date, yearly, countries, days, trade, search, occasion
CELEBRATIONS = [
    (
        ("Nouvel an", "New year", "Nový rok"),
        ("Un look qui brille pour le réveillon.", "A shining look for the party.", "Žiarivý look na oslavu."),
        D(2027, 1, 1), True, [], 10, "makeup", "paillettes", "year_end",
    ),
    (
        ("Fête du Vodoun", "Vodun day", "Sviatok Vodun"),
        ("Tresses et foulards pour le 10 janvier.", "Braids and headwraps for 10 January.", "Vrkoče a šatky na 10. januára."),
        D(2027, 1, 10), True, ["BJ"], 7, "braids", "", "",
    ),
    (
        ("Saint-Valentin", "Valentine's day", "Valentín"),
        ("Prends rendez-vous avant la foule.", "Book before the crowd.", "Rezervuj si skôr ako ostatní."),
        D(2027, 2, 14), True, [], 7, "makeup", "rouge à lèvres", "",
    ),
    (
        ("Journée des femmes", "Women's day", "Deň žien"),
        ("Le 8 mars, fais-toi belle.", "On 8 March, treat yourself.", "8. marca sa rozmaznávaj."),
        D(2027, 3, 8), True, [], 7, "hair", "", "",
    ),
    (
        ("Fin du Ramadan", "End of Ramadan", "Koniec ramadánu"),
        ("Date à confirmer selon la lune.", "Date to confirm with the moon.", "Dátum podľa mesiaca."),
        D(2027, 3, 10), False, ["BJ", "FR"], 7, "headwrap", "", "",
    ),
    (
        ("Pâques", "Easter", "Veľká noc"),
        ("Une tenue fraîche pour le dimanche.", "A fresh outfit for Sunday.", "Svieži outfit na nedeľu."),
        D(2027, 3, 28), False, [], 7, "sewing", "", "",
    ),
    (
        ("Tabaski", "Eid al-Adha", "Kurban bajram"),
        ("Date à confirmer selon la lune.", "Date to confirm with the moon.", "Dátum podľa mesiaca."),
        D(2027, 5, 16), False, ["BJ", "FR"], 10, "sewing", "pagne", "",
    ),
    (
        ("Fête des mères", "Mother's day", "Deň matiek"),
        ("Offre-lui un moment rien qu'à elle.", "Give her a moment just for her.", "Daruj jej chvíľu len pre ňu."),
        D(2027, 5, 30), False, ["BJ", "FR"], 10, "skincare", "coffret", "mothers_day",
    ),
    (
        ("Fête de l'indépendance", "Independence day", "Deň nezávislosti"),
        ("Le 1er août, aux couleurs du Bénin.", "On 1 August, in Benin's colours.", "1. augusta vo farbách Beninu."),
        D(2027, 8, 1), True, ["BJ"], 7, "sewing", "pagne", "",
    ),
    (
        ("Noël", "Christmas", "Vianoce"),
        ("Coffrets et rendez-vous de fêtes.", "Gift boxes and party appointments.", "Darčekové sady a sviatočné termíny."),
        D(2026, 12, 25), True, [], 14, "makeup", "coffret", "year_end",
    ),
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

    Prize = apps.get_model("gamification", "WheelPrize")
    if not Prize.objects.exists():
        for position, (labels, kind, points, amount, weight, stock, countries) in enumerate(PRIZES):
            Prize.objects.create(
                label=labels[0],
                label_fr=labels[0],
                label_en=labels[1],
                label_sk=labels[2],
                kind=kind,
                points=points,
                amount_off_minor=amount,
                weight=weight,
                daily_stock=stock,
                countries=countries,
                position=position,
            )
    Reward = apps.get_model("gamification", "Reward")
    if not Reward.objects.exists():
        for position, (titles, kind, cost, amount, level, countries) in enumerate(REWARDS):
            Reward.objects.create(
                title=titles[0],
                title_fr=titles[0],
                title_en=titles[1],
                title_sk=titles[2],
                kind=kind,
                cost_points=cost,
                amount_off_minor=amount,
                min_level=level,
                countries=countries,
                position=position,
            )
    Celebration = apps.get_model("gamification", "Celebration")
    Trade = apps.get_model("pros", "Trade")
    if not Celebration.objects.exists():
        for names, messages, date, yearly, countries, days, trade, search, occasion in CELEBRATIONS:
            Celebration.objects.create(
                name=names[0],
                name_fr=names[0],
                name_en=names[1],
                name_sk=names[2],
                message=messages[0],
                message_fr=messages[0],
                message_en=messages[1],
                message_sk=messages[2],
                date=date,
                yearly=yearly,
                countries=countries,
                remind_days=days,
                trade=Trade.objects.filter(key=trade).first(),
                search=search,
                gift_occasion=occasion,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("gamification", "0002_append_only_points"),
        ("core", "0004_media_documents"),
        ("notifications", "0004_contactmessage"),
        ("pros", "0007_proprofile_level_proprofile_level_at"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
