"""Switches of the academy and of the lives, prices of the courses (15 % commission on the
courses of the pros, no buyer protection), notification texts. Rows already there are
never overwritten: they are edited in the admin."""

from django.db import migrations

RULES = [
    {
        "kind": "commission",
        "name": "Courses of the pros: 15 % commission",
        "purpose": "training",
        "percent_bps": 1500,
    },
    {
        "kind": "buyer_protection",
        "name": "Courses: no buyer protection (refund within 14 days instead)",
        "purpose": "training",
        "percent_bps": 0,
    },
    {
        "kind": "buyer_protection",
        "name": "Academy pass: no buyer protection",
        "purpose": "academy_pass",
        "percent_bps": 0,
    },
    {
        "kind": "commission",
        "name": "Academy pass: no commission (the platform sells)",
        "purpose": "academy_pass",
        "percent_bps": 0,
    },
]

FLAGS = [
    ("academy", "Académie", "Formations vidéo, pass, certificats (module 7)."),
    ("lives", "Lives de formation", "Programmation des lives, inscriptions, salle d'attente."),
]

ON = {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False}

EVENTS = {
    "academy.course_published": (
        "La formation de la pro est publiée après la revue.",
        "/pro/academy",
        {
            "fr": ("Ta formation est en ligne", "« {{ course }} » est publiée dans l'Académie."),
            "en": ("Your course is online", "« {{ course }} » is published in the Academy."),
            "sk": ("Tvoj kurz je online", "« {{ course }} » je zverejnený v Akadémii."),
        },
    ),
    "academy.course_rejected": (
        "La formation de la pro est renvoyée avec une remarque de l'équipe.",
        "/pro/academy",
        {
            "fr": ("Ta formation est à revoir", "« {{ course }} » : {{ note }}"),
            "en": ("Your course needs changes", "« {{ course }} »: {{ note }}"),
            "sk": ("Tvoj kurz treba upraviť", "« {{ course }} »: {{ note }}"),
        },
    ),
    "academy.course_ready": (
        "L'élève a payé : la formation est ouverte.",
        "/academie/mes-formations",
        {
            "fr": ("Ta formation est prête", "« {{ course }} » t'attend. Bonne formation !"),
            "en": ("Your course is ready", "« {{ course }} » is waiting for you. Enjoy!"),
            "sk": ("Tvoj kurz je pripravený", "« {{ course }} » na teba čaká. Príjemné učenie!"),
        },
    ),
    "academy.course_sold": (
        "Une élève achète une formation de la pro.",
        "/pro/academy",
        {
            "fr": ("Nouvelle élève", "{{ student }} a acheté « {{ course }} »."),
            "en": ("New student", "{{ student }} bought « {{ course }} »."),
            "sk": ("Nová študentka", "{{ student }} si kúpila « {{ course }} »."),
        },
    ),
    "academy.certificate_ready": (
        "L'élève a fini la formation : son certificat est prêt.",
        "/academie/mes-formations",
        {
            "fr": ("Bravo, c'est fini !", "Ton certificat de « {{ course }} » est prêt (code {{ code }})."),
            "en": ("Well done, you finished!", "Your certificate of « {{ course }} » is ready (code {{ code }})."),
            "sk": ("Výborne, hotovo!", "Tvoj certifikát z « {{ course }} » je pripravený (kód {{ code }})."),
        },
    ),
    "academy.badge_earned": (
        "La pro obtient le badge « Formée sur Solange Glow ».",
        "/pro",
        {
            "fr": ("Badge « Formée sur Solange Glow »", "Il s'affiche sur ta vitrine et te fait monter dans la recherche."),
            "en": ("« Trained on Solange Glow » badge", "It shows on your showcase and moves you up in the search."),
            "sk": ("Odznak « Vyškolená na Solange Glow »", "Zobrazí sa na tvojom profile a posunie ťa vyššie vo vyhľadávaní."),
        },
    ),
    "academy.pass_paid": (
        "Le mois du pass est payé.",
        "/academie",
        {
            "fr": ("Ton pass est actif", "Toutes les formations du pass sont ouvertes jusqu'au {{ until }}."),
            "en": ("Your pass is on", "Every course of the pass is open until {{ until }}."),
            "sk": ("Tvoj pas je aktívny", "Všetky kurzy pasu sú otvorené do {{ until }}."),
        },
    ),
    "academy.pass_renewal_due": (
        "Quelques jours avant la fin du mois du pass : le paiement du mois suivant.",
        "/academie/pass",
        {
            "fr": ("Ton pass finit bientôt", "Il finit le {{ until }}. Paie le mois suivant pour continuer."),
            "en": ("Your pass ends soon", "It ends on {{ until }}. Pay next month to go on."),
            "sk": ("Tvoj pas čoskoro končí", "Končí {{ until }}. Zaplať ďalší mesiac a pokračuj."),
        },
    ),
    "academy.pass_ended": (
        "Le mois du pass n'est pas payé : le pass s'arrête.",
        "/academie/pass",
        {
            "fr": ("Ton pass est arrêté", "Tes progrès sont gardés. Reprends le pass quand tu veux."),
            "en": ("Your pass has stopped", "Your progress is kept. Take the pass again whenever you want."),
            "sk": ("Tvoj pas sa zastavil", "Tvoj pokrok ostáva uložený. Pas si môžeš kedykoľvek obnoviť."),
        },
    ),
    "academy.live_invitation": (
        "Les élèves d'une formation sont invitées à un live.",
        "/academie/lives",
        {
            "fr": ("Invitation à un live", "« {{ live }} » le {{ when }}. Inscris-toi pour garder ta place."),
            "en": ("Invitation to a live", "« {{ live }} » on {{ when }}. Register to keep your place."),
            "sk": ("Pozvánka na live", "« {{ live }} » {{ when }}. Prihlás sa a podrž si miesto."),
        },
    ),
    "academy.live_reminder": (
        "Rappel la veille d'un live.",
        "/academie/lives",
        {
            "fr": ("Live demain", "« {{ live }} » commence le {{ when }}."),
            "en": ("Live tomorrow", "« {{ live }} » starts on {{ when }}."),
            "sk": ("Live zajtra", "« {{ live }} » začína {{ when }}."),
        },
    ),
    "academy.live_starting": (
        "Rappel quelques minutes avant un live.",
        "/academie/lives",
        {
            "fr": ("Ça commence bientôt", "« {{ live }} » : la salle d'attente est ouverte."),
            "en": ("Starting soon", "« {{ live }} »: the waiting room is open."),
            "sk": ("Čoskoro to začne", "« {{ live }} »: čakáreň je otvorená."),
        },
    ),
    "academy.live_cancelled": (
        "Un live est annulé.",
        "/academie/lives",
        {
            "fr": ("Live annulé", "« {{ live }} » n'aura pas lieu."),
            "en": ("Live cancelled", "« {{ live }} » will not take place."),
            "sk": ("Live zrušený", "« {{ live }} » sa neuskutoční."),
        },
    ),
}


def create(apps, schema_editor):
    Flag = apps.get_model("core", "FeatureFlag")
    for key, name, description in FLAGS:
        Flag.objects.get_or_create(
            key=key, defaults={"name": name, "description": description, "is_enabled": True}
        )
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)
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
    dependencies = [
        ("academy", "0001_initial"),
        ("core", "0004_media_documents"),
        ("notifications", "0004_contactmessage"),
        ("payments", "0009_academy_pass_purpose"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
