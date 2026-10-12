from django.db import migrations

# Default texts (fr, en, sk), editable afterwards in the admin; never overwritten.
EVENTS = {
    "social.new_follower": {
        "description": "Quelqu'un suit la personne.",
        "link": "/following",
        "texts": {
            "fr": ("{{ name }} te suit", "Découvre son profil et suis-la en retour."),
            "en": ("{{ name }} follows you", "Discover her profile and follow back."),
            "sk": ("{{ name }} ťa sleduje", "Pozri si jej profil a sleduj ju späť."),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "social.comment": {
        "description": "Nouveau commentaire sur une publication.",
        "link": "/",
        "texts": {
            "fr": ("{{ name }} a commenté ta publication", "« {{ text }} »"),
            "en": ("{{ name }} commented on your post", "“{{ text }}”"),
            "sk": ("{{ name }} komentovala tvoj príspevok", "„{{ text }}“"),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "social.reply": {
        "description": "Réponse à un commentaire.",
        "link": "/",
        "texts": {
            "fr": ("{{ name }} t'a répondu", "« {{ text }} »"),
            "en": ("{{ name }} replied to you", "“{{ text }}”"),
            "sk": ("{{ name }} ti odpovedala", "„{{ text }}“"),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "social.post_published": {
        "description": "Une publication programmée vient d'être mise en ligne.",
        "link": "/",
        "texts": {
            "fr": ("Ta publication est en ligne", "Elle vient de paraître, comme prévu."),
            "en": ("Your post is online", "It has just gone online, as planned."),
            "sk": ("Tvoj príspevok je online", "Práve sa zverejnil, ako bolo naplánované."),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "reviews.received": {
        "description": "Une cliente a laissé un avis vérifié.",
        "link": "/pro",
        "texts": {
            "fr": ("Nouvel avis : {{ rating }}/5", "{{ name }} a laissé un avis. Tu peux lui répondre une fois."),
            "en": ("New review: {{ rating }}/5", "{{ name }} left a review. You can reply once."),
            "sk": ("Nové hodnotenie: {{ rating }}/5", "{{ name }} zanechala hodnotenie. Môžeš raz odpovedať."),
        },
        "channels": {"in_app": True, "email": True, "push": True, "whatsapp": False, "sms": False},
    },
    "reviews.replied": {
        "description": "La pro a répondu à l'avis.",
        "link": "/",
        "texts": {
            "fr": ("{{ name }} a répondu à ton avis", "Merci d'avoir partagé ton expérience."),
            "en": ("{{ name }} replied to your review", "Thank you for sharing your experience."),
            "sk": ("{{ name }} odpovedala na tvoje hodnotenie", "Ďakujeme, že si sa podelila o skúsenosť."),
        },
        "channels": {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False},
    },
    "moderation.content_removed": {
        "description": "Un contenu de la personne a été retiré par la modération.",
        "link": "/",
        "texts": {
            "fr": ("Un de tes contenus a été retiré", "« {{ excerpt }} » ne respecte pas les règles de Solange Glow."),
            "en": ("One of your contents was removed", "“{{ excerpt }}” does not follow the rules of Solange Glow."),
            "sk": ("Jeden z tvojich obsahov bol odstránený", "„{{ excerpt }}“ nedodržiava pravidlá Solange Glow."),
        },
        "channels": {"in_app": True, "email": True, "push": False, "whatsapp": False, "sms": False},
    },
    "moderation.sanction": {
        "description": "Sanction décidée par la modération.",
        "link": "/",
        "texts": {
            "fr": ("Décision de la modération : {{ level }}", "Respecte les règles de la communauté. Écris au support pour en parler."),
            "en": ("Moderation decision: {{ level }}", "Please follow the community rules. Write to support to talk about it."),
            "sk": ("Rozhodnutie moderácie: {{ level }}", "Dodržiavaj pravidlá komunity. Napíš podpore."),
        },
        "channels": {"in_app": True, "email": True, "push": False, "whatsapp": False, "sms": False},
    },
}


def create_templates(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, event in EVENTS.items():
        for channel, active in event["channels"].items():
            values = {"description": event["description"], "link": event["link"], "is_active": active}
            for lang, (title, body) in event["texts"].items():
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"] = values["title_fr"]
            values["body"] = values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0001_initial"),
        ("notifications", "0002_seed_templates"),
    ]

    operations = [migrations.RunPython(create_templates, migrations.RunPython.noop)]
