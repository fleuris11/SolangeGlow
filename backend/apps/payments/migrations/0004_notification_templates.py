from django.db import migrations

ON = {"in_app": True, "email": False, "push": True, "whatsapp": False, "sms": False}
WITH_EMAIL = {**ON, "email": True}
# The receipt code goes by WhatsApp and SMS too (specification); never in the stored text.
CODE = {"in_app": True, "email": True, "push": True, "whatsapp": True, "sms": True}

# Default texts (fr, en, sk), editable afterwards in the admin; never overwritten.
EVENTS = {
    "payments.paid": {
        "description": "Paiement reçu : la cliente reçoit son code de réception.",
        "channels": CODE,
        "texts": {
            "fr": (
                "Paiement reçu ({{ reference }})",
                "{{ amount }} bloqués jusqu'à la réception. Ton code de réception : {{ code }}. "
                "Donne-le seulement quand tu as ta commande en main.",
            ),
            "en": (
                "Payment received ({{ reference }})",
                "{{ amount }} held until you receive it. Your receipt code: {{ code }}. "
                "Give it only once you hold your order.",
            ),
            "sk": (
                "Platba prijatá ({{ reference }})",
                "{{ amount }} blokované do prevzatia. Tvoj kód prevzatia: {{ code }}. "
                "Daj ho až keď máš objednávku v rukách.",
            ),
        },
    },
    # Shown in the app: the code itself stays in the payment page.
    "payments.paid#in_app": {
        "fr": "{{ amount }} bloqués jusqu'à la réception. Ton code est dans le détail du paiement.",
        "en": "{{ amount }} held until you receive it. Your code is in the payment details.",
        "sk": "{{ amount }} blokované do prevzatia. Kód nájdeš v detaile platby.",
    },
    "payments.new_code#in_app": {
        "fr": "Ton nouveau code est dans le détail du paiement.",
        "en": "Your new code is in the payment details.",
        "sk": "Tvoj nový kód nájdeš v detaile platby.",
    },
    "payments.new_code": {
        "description": "Nouveau code de réception demandé par la cliente.",
        "channels": CODE,
        "texts": {
            "fr": ("Ton nouveau code ({{ reference }})", "Nouveau code de réception : {{ code }}."),
            "en": ("Your new code ({{ reference }})", "New receipt code: {{ code }}."),
            "sk": ("Tvoj nový kód ({{ reference }})", "Nový kód prevzatia: {{ code }}."),
        },
    },
    "payments.new_sale": {
        "description": "Commande payée : la vendeuse doit expédier.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": (
                "Nouvelle commande payée ({{ reference }})",
                "{{ amount }} t'attendent. Expédie ou remets la commande dans les {{ days }} jours.",
            ),
            "en": (
                "New paid order ({{ reference }})",
                "{{ amount }} are waiting for you. Ship or hand over the order within {{ days }} days.",
            ),
            "sk": (
                "Nová zaplatená objednávka ({{ reference }})",
                "Čaká ťa {{ amount }}. Odošli alebo odovzdaj objednávku do {{ days }} dní.",
            ),
        },
    },
    "payments.ship_reminder": {
        "description": "Rappel à la vendeuse avant la date limite d'envoi.",
        "channels": ON,
        "texts": {
            "fr": (
                "Pense à expédier ({{ reference }})",
                "Sans envoi avant le {{ deadline }}, la commande sera annulée et la cliente remboursée.",
            ),
            "en": (
                "Remember to ship ({{ reference }})",
                "Without shipping before {{ deadline }}, the order is cancelled and the client refunded.",
            ),
            "sk": (
                "Nezabudni odoslať ({{ reference }})",
                "Bez odoslania do {{ deadline }} sa objednávka zruší a klientke sa vrátia peniaze.",
            ),
        },
    },
    "payments.shipped": {
        "description": "La commande est partie.",
        "channels": ON,
        "texts": {
            "fr": ("Ta commande est en route ({{ reference }})", "Garde ton code pour la remise."),
            "en": ("Your order is on its way ({{ reference }})", "Keep your code for the handover."),
            "sk": ("Tvoja objednávka je na ceste ({{ reference }})", "Kód si nechaj na odovzdanie."),
        },
    },
    "payments.delivered": {
        "description": "La vendeuse indique la commande livrée (photo à l'appui).",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": (
                "Commande livrée ? ({{ reference }})",
                "Si tu l'as reçue, donne ton code. Sinon, signale-le dans l'appli.",
            ),
            "en": (
                "Order delivered? ({{ reference }})",
                "If you got it, give your code. If not, tell us in the app.",
            ),
            "sk": (
                "Objednávka doručená? ({{ reference }})",
                "Ak ju máš, daj svoj kód. Ak nie, nahlás to v aplikácii.",
            ),
        },
    },
    "payments.release_reminder": {
        "description": "Relance de la cliente après une livraison sans code.",
        "channels": ON,
        "texts": {
            "fr": (
                "As-tu reçu ta commande ? ({{ reference }})",
                "Sans réponse, l'argent sera versé à la vendeuse. Un problème ? Signale-le.",
            ),
            "en": (
                "Did you get your order? ({{ reference }})",
                "Without an answer, the money goes to the seller. A problem? Tell us.",
            ),
            "sk": (
                "Dostala si objednávku? ({{ reference }})",
                "Bez odpovede pôjdu peniaze predávajúcej. Problém? Nahlás ho.",
            ),
        },
    },
    "payments.code_locked": {
        "description": "Trop de codes faux saisis.",
        "channels": ON,
        "texts": {
            "fr": (
                "Code bloqué ({{ reference }})",
                "Trop de codes faux. Si tu as bien ta commande, demande un nouveau code dans l'appli.",
            ),
            "en": (
                "Code locked ({{ reference }})",
                "Too many wrong codes. If you have your order, ask for a new code in the app.",
            ),
            "sk": (
                "Kód zablokovaný ({{ reference }})",
                "Priveľa chybných kódov. Ak máš objednávku, požiadaj v aplikácii o nový kód.",
            ),
        },
    },
    "payments.released": {
        "description": "Argent disponible pour la vendeuse.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("{{ amount }} disponibles", "Commande {{ reference }} terminée : retire ton argent quand tu veux."),
            "en": ("{{ amount }} available", "Order {{ reference }} completed: take your money when you want."),
            "sk": ("{{ amount }} k dispozícii", "Objednávka {{ reference }} dokončená: vyber si peniaze kedykoľvek."),
        },
    },
    "payments.completed": {
        "description": "Commande terminée côté cliente.",
        "channels": {**ON, "push": False},
        "texts": {
            "fr": ("Commande terminée ({{ reference }})", "Merci ! Tu peux laisser un avis."),
            "en": ("Order completed ({{ reference }})", "Thank you! You can leave a review."),
            "sk": ("Objednávka dokončená ({{ reference }})", "Ďakujeme! Môžeš zanechať hodnotenie."),
        },
    },
    "payments.refunded": {
        "description": "Remboursement de la cliente.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("Remboursement de {{ amount }}", "Commande {{ reference }} : ton argent revient sur ton moyen de paiement."),
            "en": ("Refund of {{ amount }}", "Order {{ reference }}: your money goes back to your payment method."),
            "sk": ("Vrátenie {{ amount }}", "Objednávka {{ reference }}: peniaze sa vrátia na tvoj spôsob platby."),
        },
    },
    "payments.sale_cancelled": {
        "description": "Vente annulée, cliente remboursée.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("Vente annulée ({{ reference }})", "La cliente a été remboursée."),
            "en": ("Sale cancelled ({{ reference }})", "The client was refunded."),
            "sk": ("Predaj zrušený ({{ reference }})", "Klientke boli vrátené peniaze."),
        },
    },
    "disputes.opened": {
        "description": "Litige ouvert : argent gelé, salle à trois.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": (
                "Litige ouvert ({{ reference }})",
                "L'argent est gelé. Dépose tes preuves et réponds dans les {{ hours }} heures.",
            ),
            "en": (
                "Dispute opened ({{ reference }})",
                "The money is frozen. Add your evidence and answer within {{ hours }} hours.",
            ),
            "sk": (
                "Spor otvorený ({{ reference }})",
                "Peniaze sú zmrazené. Pridaj dôkazy a odpovedz do {{ hours }} hodín.",
            ),
        },
    },
    "disputes.reminder": {
        "description": "Rappel à mi-délai d'un litige.",
        "channels": ON,
        "texts": {
            "fr": ("Litige : pense à répondre ({{ reference }})", "Le délai pour déposer tes preuves se termine bientôt."),
            "en": ("Dispute: remember to answer ({{ reference }})", "The time to add your evidence ends soon."),
            "sk": ("Spor: nezabudni odpovedať ({{ reference }})", "Čas na pridanie dôkazov čoskoro uplynie."),
        },
    },
    "disputes.decided": {
        "description": "Décision d'un litige.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("Litige tranché ({{ reference }})", "Décision : {{ decision }}. Remboursé : {{ refunded }}."),
            "en": ("Dispute decided ({{ reference }})", "Decision: {{ decision }}. Refunded: {{ refunded }}."),
            "sk": ("Spor rozhodnutý ({{ reference }})", "Rozhodnutie: {{ decision }}. Vrátené: {{ refunded }}."),
        },
    },
    "payouts.paid": {
        "description": "Versement envoyé à la pro.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("Versement de {{ amount }} envoyé", "Ton argent est en route vers ton compte."),
            "en": ("Payout of {{ amount }} sent", "Your money is on its way to your account."),
            "sk": ("Výplata {{ amount }} odoslaná", "Peniaze sú na ceste na tvoj účet."),
        },
    },
    "payouts.failed": {
        "description": "Versement échoué, argent de nouveau disponible.",
        "channels": WITH_EMAIL,
        "texts": {
            "fr": ("Versement de {{ amount }} échoué", "L'argent est de nouveau disponible. Vérifie ton moyen de versement."),
            "en": ("Payout of {{ amount }} failed", "The money is available again. Check your payout method."),
            "sk": ("Výplata {{ amount }} zlyhala", "Peniaze sú opäť k dispozícii. Skontroluj spôsob výplaty."),
        },
    },
}


def create_templates(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    for event_key, event in EVENTS.items():
        if "#" in event_key:
            continue
        link = "/pro/wallet" if event_key.startswith("payouts.") else "/payments"
        for channel, active in event["channels"].items():
            values = {"description": event["description"], "link": link, "is_active": active}
            for lang, (title, body) in event["texts"].items():
                if channel == "in_app" and f"{event_key}#in_app" in EVENTS:
                    body = EVENTS[f"{event_key}#in_app"][lang]
                values[f"title_{lang}"] = title
                values[f"body_{lang}"] = body
            values["title"] = values["title_fr"]
            values["body"] = values["body_fr"]
            Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_default_pricing_rules"),
        ("notifications", "0003_notificationdelivery_sensitive"),
    ]

    operations = [migrations.RunPython(create_templates, migrations.RunPython.noop)]
