"""The « booking » switch and the notification texts of appointments. Rows already there
are never overwritten (edited in the admin).

Client events also have WhatsApp and SMS texts: a guest (no account) only gets those.
"""

from django.db import migrations

ON = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
GUEST = {**ON, "whatsapp": True, "sms": True}

CLIENT = "/appointments"
PRO = "/pro/agenda"

EVENTS = {
    # --- To the client ---------------------------------------------------------------------
    "booking.confirmed": (
        "Le rendez-vous de la cliente est confirmé.",
        GUEST,
        CLIENT,
        {
            "fr": ("Rendez-vous confirmé", "{{ service }} chez {{ pro }}, {{ when }}. Réf. {{ reference }}. Gérer : {{ link }}"),
            "en": ("Appointment confirmed", "{{ service }} at {{ pro }}, {{ when }}. Ref. {{ reference }}. Manage: {{ link }}"),
            "sk": ("Termín potvrdený", "{{ service }} u {{ pro }}, {{ when }}. Ref. {{ reference }}. Spravovať: {{ link }}"),
        },
    ),
    "booking.requested": (
        "La demande de la cliente attend la réponse de la pro.",
        GUEST,
        CLIENT,
        {
            "fr": ("Demande envoyée", "{{ pro }} va répondre à ta demande : {{ service }}, {{ when }}. Suivre : {{ link }}"),
            "en": ("Request sent", "{{ pro }} will answer your request: {{ service }}, {{ when }}. Follow: {{ link }}"),
            "sk": ("Žiadosť odoslaná", "{{ pro }} odpovie na tvoju žiadosť: {{ service }}, {{ when }}. Sledovať: {{ link }}"),
        },
    ),
    "booking.declined": (
        "La pro refuse la demande (l'acompte est rendu).",
        GUEST,
        CLIENT,
        {
            "fr": ("Demande refusée", "{{ pro }} ne peut pas te recevoir {{ when }}. {{ message }}"),
            "en": ("Request declined", "{{ pro }} cannot see you {{ when }}. {{ message }}"),
            "sk": ("Žiadosť zamietnutá", "{{ pro }} ťa nemôže prijať {{ when }}. {{ message }}"),
        },
    ),
    "booking.proposed": (
        "La pro propose un autre créneau à la cliente.",
        GUEST,
        CLIENT,
        {
            "fr": ("Un autre créneau proposé", "{{ pro }} te propose {{ when }} pour {{ service }}. {{ message }} Répondre : {{ link }}"),
            "en": ("Another time proposed", "{{ pro }} proposes {{ when }} for {{ service }}. {{ message }} Answer: {{ link }}"),
            "sk": ("Navrhnutý iný čas", "{{ pro }} navrhuje {{ when }} pre {{ service }}. {{ message }} Odpovedať: {{ link }}"),
        },
    ),
    "booking.cancelled": (
        "La cliente a annulé son rendez-vous.",
        GUEST,
        CLIENT,
        {
            "fr": ("Rendez-vous annulé", "Ton rendez-vous {{ service }} chez {{ pro }} ({{ when }}) est annulé.{% if late %} Annulé tard : l'acompte reste à la pro.{% endif %}"),
            "en": ("Appointment cancelled", "Your appointment {{ service }} at {{ pro }} ({{ when }}) is cancelled.{% if late %} Cancelled late: the pro keeps the deposit.{% endif %}"),
            "sk": ("Termín zrušený", "Tvoj termín {{ service }} u {{ pro }} ({{ when }}) je zrušený.{% if late %} Zrušené neskoro: záloha zostáva profesionálke.{% endif %}"),
        },
    ),
    "booking.cancelled_by_pro": (
        "La pro (ou le système) annule le rendez-vous : la cliente est remboursée.",
        GUEST,
        CLIENT,
        {
            "fr": ("Rendez-vous annulé", "{{ pro }} a annulé ton rendez-vous {{ service }} ({{ when }}). Ton acompte t'est rendu."),
            "en": ("Appointment cancelled", "{{ pro }} cancelled your appointment {{ service }} ({{ when }}). Your deposit is refunded."),
            "sk": ("Termín zrušený", "{{ pro }} zrušila tvoj termín {{ service }} ({{ when }}). Záloha ti bude vrátená."),
        },
    ),
    "booking.moved": (
        "La pro a déplacé le rendez-vous.",
        GUEST,
        CLIENT,
        {
            "fr": ("Rendez-vous déplacé", "{{ pro }} a déplacé ton rendez-vous {{ service }} : {{ when }}. Gérer : {{ link }}"),
            "en": ("Appointment moved", "{{ pro }} moved your appointment {{ service }}: {{ when }}. Manage: {{ link }}"),
            "sk": ("Termín presunutý", "{{ pro }} presunula tvoj termín {{ service }}: {{ when }}. Spravovať: {{ link }}"),
        },
    ),
    "booking.reminder": (
        "Rappel avant le rendez-vous (24 h et 2 h avant par défaut).",
        GUEST,
        CLIENT,
        {
            "fr": ("Rappel de rendez-vous", "{{ service }} chez {{ pro }}, {{ when }}. Un empêchement ? Préviens ici : {{ link }}"),
            "en": ("Appointment reminder", "{{ service }} at {{ pro }}, {{ when }}. Can't come? Tell her here: {{ link }}"),
            "sk": ("Pripomienka termínu", "{{ service }} u {{ pro }}, {{ when }}. Nemôžeš prísť? Daj vedieť tu: {{ link }}"),
        },
    ),
    "booking.completed": (
        "Le rendez-vous est terminé : la cliente peut laisser un avis.",
        GUEST,
        CLIENT,
        {
            "fr": ("Merci pour ta visite", "Comment s'est passé {{ service }} chez {{ pro }} ? Donne ton avis : {{ link }}"),
            "en": ("Thank you for your visit", "How was {{ service }} at {{ pro }}? Leave a review: {{ link }}"),
            "sk": ("Ďakujeme za návštevu", "Aké bolo {{ service }} u {{ pro }}? Ohodnoť: {{ link }}"),
        },
    ),
    "booking.no_show": (
        "La cliente est marquée absente.",
        GUEST,
        CLIENT,
        {
            "fr": ("Rendez-vous manqué", "Tu n'es pas venue à ton rendez-vous {{ service }} chez {{ pro }} ({{ when }})."),
            "en": ("Missed appointment", "You did not come to your appointment {{ service }} at {{ pro }} ({{ when }})."),
            "sk": ("Zmeškaný termín", "Neprišla si na termín {{ service }} u {{ pro }} ({{ when }})."),
        },
    ),
    "booking.waitlist_offer": (
        "Une place se libère pour la cliente de la liste d'attente.",
        GUEST,
        CLIENT,
        {
            "fr": ("Une place se libère !", "{{ pro }} : {{ service }}, {{ when }}. Gardée pour toi {{ minutes }} min. Réserver : {{ link }}"),
            "en": ("A place is free!", "{{ pro }}: {{ service }}, {{ when }}. Kept for you {{ minutes }} min. Book: {{ link }}"),
            "sk": ("Uvoľnilo sa miesto!", "{{ pro }}: {{ service }}, {{ when }}. Držíme ho {{ minutes }} min. Rezervovať: {{ link }}"),
        },
    ),
    "booking.advice": (
        "La pro conseille un produit de sa boutique après le rendez-vous.",
        GUEST,
        CLIENT,
        {
            "fr": ("Un conseil de {{ pro }}", "Pour entretenir ton {{ service }} : {{ product }}. Voir : {{ link }}"),
            "en": ("Advice from {{ pro }}", "To care for your {{ service }}: {{ product }}. See: {{ link }}"),
            "sk": ("Rada od {{ pro }}", "Na starostlivosť o {{ service }}: {{ product }}. Pozrieť: {{ link }}"),
        },
    ),
    "booking.last_minute": (
        "Créneaux de dernière minute à prix réduit près de chez la cliente (une alerte par jour au plus).",
        ON,
        CLIENT,
        {
            "fr": ("Dernière minute : -{{ percent }} %", "{{ pro }} a des places libres bientôt, à -{{ percent }} %."),
            "en": ("Last minute: -{{ percent }}%", "{{ pro }} has free places soon, -{{ percent }}%."),
            "sk": ("Last minute: -{{ percent }} %", "{{ pro }} má čoskoro voľné miesta, -{{ percent }} %."),
        },
    ),
    # --- To the pro and her collaborators ---------------------------------------------------
    "booking.new": (
        "Nouveau rendez-vous dans l'agenda.",
        {**ON, "whatsapp": True},
        PRO,
        {
            "fr": ("Nouveau rendez-vous", "{{ client }} : {{ service }}, {{ when }}."),
            "en": ("New appointment", "{{ client }}: {{ service }}, {{ when }}."),
            "sk": ("Nový termín", "{{ client }}: {{ service }}, {{ when }}."),
        },
    ),
    "booking.request": (
        "Une demande attend la réponse de la pro (confirmation manuelle).",
        {**ON, "whatsapp": True},
        PRO,
        {
            "fr": ("Demande de rendez-vous", "{{ client }} demande {{ service }}, {{ when }}. Accepte, refuse ou propose un autre créneau."),
            "en": ("Booking request", "{{ client }} asks for {{ service }}, {{ when }}. Accept, decline or propose another time."),
            "sk": ("Žiadosť o termín", "{{ client }} žiada {{ service }}, {{ when }}. Prijmi, odmietni alebo navrhni iný čas."),
        },
    ),
    "booking.proposal_accepted": (
        "La cliente accepte le créneau proposé.",
        ON,
        PRO,
        {
            "fr": ("Créneau accepté", "{{ client }} accepte {{ when }} pour {{ service }}."),
            "en": ("Time accepted", "{{ client }} accepts {{ when }} for {{ service }}."),
            "sk": ("Čas prijatý", "{{ client }} prijíma {{ when }} pre {{ service }}."),
        },
    ),
    "booking.proposal_refused": (
        "La cliente refuse le créneau proposé.",
        ON,
        PRO,
        {
            "fr": ("Créneau refusé", "{{ client }} ne peut pas venir {{ when }} ({{ service }})."),
            "en": ("Time declined", "{{ client }} cannot come {{ when }} ({{ service }})."),
            "sk": ("Čas odmietnutý", "{{ client }} nemôže prísť {{ when }} ({{ service }})."),
        },
    ),
    "booking.cancelled_by_client": (
        "La cliente annule son rendez-vous.",
        {**ON, "whatsapp": True},
        PRO,
        {
            "fr": ("Rendez-vous annulé", "{{ client }} a annulé {{ service }}, {{ when }}."),
            "en": ("Appointment cancelled", "{{ client }} cancelled {{ service }}, {{ when }}."),
            "sk": ("Termín zrušený", "{{ client }} zrušila {{ service }}, {{ when }}."),
        },
    ),
    "booking.group": (
        "Une réservation de groupe arrive dans l'agenda.",
        ON,
        PRO,
        {
            "fr": ("Réservation de groupe", "{{ client }} réserve pour {{ size }} personnes : {{ service }}, {{ when }}."),
            "en": ("Group booking", "{{ client }} books for {{ size }} people: {{ service }}, {{ when }}."),
            "sk": ("Skupinová rezervácia", "{{ client }} rezervuje pre {{ size }} osôb: {{ service }}, {{ when }}."),
        },
    ),
    "booking.invited": (
        "Une pro ajoute la personne à l'agenda de son salon.",
        {**ON, "whatsapp": True},
        PRO,
        {
            "fr": ("Bienvenue dans l'équipe", "{{ pro }} t'a ajoutée à son agenda. Tes rendez-vous sont ici."),
            "en": ("Welcome to the team", "{{ pro }} added you to her agenda. Your appointments are here."),
            "sk": ("Vitaj v tíme", "{{ pro }} ťa pridala do svojho kalendára. Tvoje termíny sú tu."),
        },
    ),
}


def create(apps, schema_editor):
    Flag = apps.get_model("core", "FeatureFlag")
    Flag.objects.get_or_create(
        key="booking",
        defaults={
            "name": "Prise de rendez-vous",
            "description": "Réservation en ligne, agenda et liste d'attente (module 8).",
            "is_enabled": True,
        },
    )
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, (description, channels, link, texts) in EVENTS.items():
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
        ("booking", "0001_initial"),
        ("core", "0003_alter_featureflag_roles"),
        ("notifications", "0004_contactmessage"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
