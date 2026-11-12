"""The address of a prospect (shown on their prepared showcase), and the standard e-mail
« Your showcase is ready » rewritten: the showcase is now online when it is sent. A text
already changed in the admin is kept."""

import importlib

from django.db import migrations, models

FIRST = importlib.import_module("apps.backoffice.migrations.0004_prospect_emails")

READY = {
    "fr": (
        "{{ name }}, le travail de {{ business }} est en lumière sur Solange Glow",
        "Bonjour {{ name }},\n\n"
        "Nous mettons en lumière le travail de {{ business }}{% if activity %} "
        "({{ activity }}){% endif %} sur Solange Glow, la plateforme beauté et mode. "
        "Votre vitrine est en ligne, à votre nom, avec vos réalisations et votre contact :\n"
        "{{ showcase_link }}\n\n"
        "{{ pitch }}\n\n"
        "Cette vitrine est à vous. Choisissez votre mot de passe pour la modifier, ajouter vos "
        "prestations et recevoir vos rendez-vous :\n{{ link }}\n\n"
        "Tout est gratuit : rendez-vous en ligne et agenda, boutique, formations et cours en "
        "direct, et notre publicité sur les réseaux sociaux.\n\n"
        "Ce lien est personnel et fonctionne 14 jours. Une question ? Répondez à cet e-mail.",
    ),
    "en": (
        "{{ name }}, the work of {{ business }} is in the spotlight on Solange Glow",
        "Hello {{ name }},\n\n"
        "We are putting the work of {{ business }}{% if activity %} ({{ activity }}){% endif %} "
        "in the spotlight on Solange Glow, the beauty and fashion platform. Your showcase is "
        "online, in your name, with your work and your contact:\n{{ showcase_link }}\n\n"
        "{{ pitch }}\n\n"
        "This showcase is yours. Choose your password to change it, add your services and "
        "receive your bookings:\n{{ link }}\n\n"
        "Everything is free: online bookings and agenda, shop, courses and live classes, and "
        "our advertising on social networks.\n\n"
        "This link is personal and works for 14 days. A question? Answer this e-mail.",
    ),
    "sk": (
        "{{ name }}, práca {{ business }} je v centre pozornosti na Solange Glow",
        "Dobrý deň, {{ name }},\n\n"
        "Na Solange Glow, platforme krásy a módy, predstavujeme prácu {{ business }}"
        "{% if activity %} ({{ activity }}){% endif %}. Vaša prezentácia je online, pod vaším "
        "menom, s vašimi prácami a kontaktom:\n{{ showcase_link }}\n\n"
        "{{ pitch }}\n\n"
        "Táto prezentácia patrí vám. Vyberte si heslo, upravte ju, pridajte svoje služby "
        "a prijímajte rezervácie:\n{{ link }}\n\n"
        "Všetko je zadarmo: online rezervácie a kalendár, obchod, kurzy a živé vysielania "
        "a naša reklama na sociálnych sieťach.\n\n"
        "Tento odkaz je osobný a platí 14 dní. Máte otázku? Odpovedzte na tento e-mail.",
    ),
}


def _full(language: str, body: str) -> str:
    return f"{body}\n\n{FIRST.SIGN[language]}\n\n{FIRST.STOP[language]}"


def rewrite(apps, schema_editor):
    Template = apps.get_model("backoffice", "ProspectEmailTemplate")
    template = Template.objects.filter(key="showcase_ready").first()
    if template is None:
        return
    original = next(row for row in FIRST.TEMPLATES if row["key"] == "showcase_ready")
    changed = []
    for language in ("fr", "en", "sk"):
        old_subject, old_body = original[language]
        if getattr(template, f"body_{language}") != _full(language, old_body):
            continue  # Changed in the admin: kept as it is.
        subject, body = READY[language]
        setattr(template, f"subject_{language}", subject)
        setattr(template, f"body_{language}", _full(language, body))
        changed.append(language)
    if "fr" in changed:
        template.subject, template.body = template.subject_fr, template.body_fr
    if changed:
        template.name = "2. Votre vitrine est en ligne"
        template.save()


class Migration(migrations.Migration):
    dependencies = [("backoffice", "0004_prospect_emails")]

    operations = [
        migrations.AddField(
            model_name="prospect",
            name="address",
            field=models.CharField(
                blank=True,
                help_text="Shown on the prepared showcase.",
                max_length=200,
                verbose_name="address",
            ),
        ),
        migrations.RunPython(rewrite, migrations.RunPython.noop),
    ]
