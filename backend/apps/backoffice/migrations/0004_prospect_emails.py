"""The first standard e-mails for the prospects, in French, English and Slovak. Rows already
there are never overwritten: they are edited in the admin (« Standard e-mails »)."""

from django.db import migrations

STOP = {
    "fr": "Vous ne souhaitez plus recevoir nos messages ? {{ stop_link }}",
    "en": "You do not want to hear from us again? {{ stop_link }}",
    "sk": "Nechcete od nás dostávať ďalšie správy? {{ stop_link }}",
}
SIGN = {
    "fr": "L'équipe Solange Glow\nhttps://solangeglow.com",
    "en": "The Solange Glow team\nhttps://solangeglow.com",
    "sk": "Tím Solange Glow\nhttps://solangeglow.com",
}

TEMPLATES = [
    {
        "key": "presentation",
        "name": "1. Présentation de Solange Glow",
        "needs_showcase": False,
        "position": 1,
        "fr": (
            "{{ business }} : votre vitrine et vos rendez-vous en ligne, gratuitement",
            "Bonjour {{ name }},\n\n"
            "Solange Glow est la plateforme beauté et mode où les clients trouvent leur "
            "professionnel, réservent et achètent, en France, au Bénin et en Slovaquie.\n\n"
            "{{ pitch }}\n\n"
            "Ce que {{ business }} obtient, gratuitement :\n"
            "- une vitrine en ligne à votre nom : photos, prestations, horaires, avis ;\n"
            "- la prise de rendez-vous en ligne et votre agenda, sans commission ni abonnement ;\n"
            "- une boutique pour vendre vos produits ;\n"
            "- des formations et des cours en direct à proposer à votre public ;\n"
            "- notre publicité sur les réseaux sociaux, qui met en avant les professionnels inscrits.\n\n"
            "Créez votre vitrine en quelques minutes :\n{{ link }}\n\n"
            "Une question ? Répondez simplement à cet e-mail.",
        ),
        "en": (
            "{{ business }}: your showcase and online bookings, free",
            "Hello {{ name }},\n\n"
            "Solange Glow is the beauty and fashion platform where clients find their "
            "professional, book and buy, in France, Benin and Slovakia.\n\n"
            "{{ pitch }}\n\n"
            "What {{ business }} gets, free:\n"
            "- an online showcase in your name: photos, services, opening hours, reviews;\n"
            "- online booking and your agenda, with no commission and no subscription;\n"
            "- a shop to sell your products;\n"
            "- courses and live classes to offer your audience;\n"
            "- our advertising on social networks, which puts registered professionals forward.\n\n"
            "Create your showcase in a few minutes:\n{{ link }}\n\n"
            "A question? Simply answer this e-mail.",
        ),
        "sk": (
            "{{ business }}: vaša prezentácia a online rezervácie zadarmo",
            "Dobrý deň, {{ name }},\n\n"
            "Solange Glow je platforma krásy a módy, kde klienti nájdu svojho profesionála, "
            "rezervujú si termín a nakupujú, vo Francúzsku, Benine a na Slovensku.\n\n"
            "{{ pitch }}\n\n"
            "Čo {{ business }} získa zadarmo:\n"
            "- online prezentáciu pod vaším menom: fotky, služby, otváracie hodiny, recenzie;\n"
            "- online rezervácie a kalendár bez provízie a bez predplatného;\n"
            "- obchod na predaj vašich produktov;\n"
            "- kurzy a živé vysielania pre vaše publikum;\n"
            "- našu reklamu na sociálnych sieťach, ktorá zviditeľňuje registrovaných profesionálov.\n\n"
            "Vytvorte si prezentáciu za pár minút:\n{{ link }}\n\n"
            "Máte otázku? Jednoducho odpovedzte na tento e-mail.",
        ),
    },
    {
        "key": "showcase_ready",
        "name": "2. Votre vitrine est prête",
        "needs_showcase": True,
        "position": 2,
        "fr": (
            "{{ name }}, la vitrine de {{ business }} est prête",
            "Bonjour {{ name }},\n\n"
            "Nous avons préparé pour vous la vitrine de {{ business }} sur Solange Glow, "
            "à partir de ce que vous présentez déjà à vos clients.\n\n"
            "{{ pitch }}\n\n"
            "Elle n'est pas encore en ligne : vous seul décidez. Choisissez votre mot de passe "
            "pour la découvrir, la corriger et la publier :\n{{ link }}\n\n"
            "Ensuite, tout est gratuit : vos rendez-vous en ligne et votre agenda, votre boutique, "
            "vos formations et vos cours en direct, et notre publicité sur les réseaux sociaux.\n\n"
            "Ce lien est personnel et fonctionne 14 jours. Une question ? Répondez à cet e-mail.",
        ),
        "en": (
            "{{ name }}, the showcase of {{ business }} is ready",
            "Hello {{ name }},\n\n"
            "We prepared the showcase of {{ business }} on Solange Glow for you, from what you "
            "already show your clients.\n\n"
            "{{ pitch }}\n\n"
            "It is not online yet: you alone decide. Choose your password to discover it, "
            "correct it and publish it:\n{{ link }}\n\n"
            "Then everything is free: online bookings and your agenda, your shop, your courses "
            "and live classes, and our advertising on social networks.\n\n"
            "This link is personal and works for 14 days. A question? Answer this e-mail.",
        ),
        "sk": (
            "{{ name }}, prezentácia {{ business }} je pripravená",
            "Dobrý deň, {{ name }},\n\n"
            "Pripravili sme pre vás prezentáciu {{ business }} na Solange Glow z toho, čo už "
            "ukazujete svojim klientom.\n\n"
            "{{ pitch }}\n\n"
            "Ešte nie je online: rozhodujete len vy. Vyberte si heslo, pozrite si ju, upravte "
            "a zverejnite:\n{{ link }}\n\n"
            "Potom je všetko zadarmo: online rezervácie a kalendár, váš obchod, kurzy a živé "
            "vysielania a naša reklama na sociálnych sieťach.\n\n"
            "Tento odkaz je osobný a platí 14 dní. Máte otázku? Odpovedzte na tento e-mail.",
        ),
    },
    {
        "key": "reminder",
        "name": "3. Relance",
        "needs_showcase": False,
        "position": 3,
        "fr": (
            "{{ name }}, une place vous attend sur Solange Glow",
            "Bonjour {{ name }},\n\n"
            "Je me permets de revenir vers vous : la vitrine de {{ business }} peut être en ligne "
            "aujourd'hui, gratuitement, avec la prise de rendez-vous et notre publicité sur les "
            "réseaux sociaux.\n\n"
            "Il suffit de quelques minutes :\n{{ link }}\n\n"
            "Si ce n'est pas le bon moment, répondez-moi : nous pouvons aussi préparer la vitrine "
            "pour vous.",
        ),
        "en": (
            "{{ name }}, a place is waiting for you on Solange Glow",
            "Hello {{ name }},\n\n"
            "A quick follow-up: the showcase of {{ business }} can be online today, free, with "
            "online booking and our advertising on social networks.\n\n"
            "It takes a few minutes:\n{{ link }}\n\n"
            "If this is not the right time, answer me: we can also prepare the showcase for you.",
        ),
        "sk": (
            "{{ name }}, na Solange Glow na vás čaká miesto",
            "Dobrý deň, {{ name }},\n\n"
            "Dovoľujem si pripomenúť: prezentácia {{ business }} môže byť online už dnes, "
            "zadarmo, s online rezerváciami a našou reklamou na sociálnych sieťach.\n\n"
            "Stačí pár minút:\n{{ link }}\n\n"
            "Ak teraz nie je vhodná chvíľa, odpovedzte mi: prezentáciu vám môžeme pripraviť aj my.",
        ),
    },
]


def create(apps, schema_editor):
    Template = apps.get_model("backoffice", "ProspectEmailTemplate")
    for row in TEMPLATES:
        values = {
            "name": row["name"],
            "needs_showcase": row["needs_showcase"],
            "position": row["position"],
        }
        for language in ("fr", "en", "sk"):
            subject, body = row[language]
            values[f"subject_{language}"] = subject
            values[f"body_{language}"] = f"{body}\n\n{SIGN[language]}\n\n{STOP[language]}"
        values["subject"], values["body"] = values["subject_fr"], values["body_fr"]
        Template.objects.get_or_create(key=row["key"], defaults=values)


class Migration(migrations.Migration):
    dependencies = [("backoffice", "0003_prospecting")]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
