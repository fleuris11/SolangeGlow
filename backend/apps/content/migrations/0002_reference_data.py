"""First pages (drafts to be checked by a lawyer before the launch), a first FAQ and the
message sent when the team answers a ticket. Rows already there are never overwritten:
they are edited in the admin."""

from django.db import migrations

DRAFT = {
    "fr": "Brouillon à faire relire et valider par un juriste avant le lancement.",
    "en": "Draft to be checked and approved by a lawyer before the launch.",
    "sk": "Návrh, ktorý musí pred spustením skontrolovať a schváliť právnik.",
}

PAGES = [
    (
        "conditions-generales",
        "terms",
        {
            "fr": (
                "Conditions générales d'utilisation et de vente",
                "Les règles d'utilisation de Solange Glow et des achats.",
                "# Objet\n\nSolange Glow met en relation des clientes et des professionnelles de la beauté et de la mode, au Bénin et en France.\n\n# Paiement sécurisé\n\nL'argent d'une commande reste bloqué jusqu'au code de réception. En cas de problème, un litige peut être ouvert.\n\n# Annulations et remboursements\n\nLes délais et règles d'annulation sont affichés avant chaque paiement.",
            ),
            "en": (
                "Terms of use and sale",
                "The rules for using Solange Glow and for purchases.",
                "# Purpose\n\nSolange Glow connects clients with beauty and fashion professionals, in Benin and in France.\n\n# Secure payment\n\nThe money of an order is held until the receipt code. If something goes wrong, a dispute can be opened.\n\n# Cancellations and refunds\n\nThe deadlines and cancellation rules are shown before each payment.",
            ),
            "sk": (
                "Podmienky používania a predaja",
                "Pravidlá používania Solange Glow a nákupov.",
                "# Účel\n\nSolange Glow spája klientky s profesionálkami krásy a módy v Benine a vo Francúzsku.\n\n# Bezpečná platba\n\nPeniaze za objednávku sú zablokované až do kódu prevzatia. Ak nastane problém, môže sa otvoriť spor.\n\n# Zrušenie a vrátenie peňazí\n\nLehoty a pravidlá zrušenia sa zobrazia pred každou platbou.",
            ),
        },
    ),
    (
        "confidentialite",
        "privacy",
        {
            "fr": (
                "Politique de confidentialité",
                "Les données que nous gardons, pourquoi, et tes droits.",
                "# Données gardées\n\nTon numéro ou ton e-mail, ton profil, tes commandes et tes rendez-vous, pour faire marcher l'appli.\n\n# Tes droits\n\nTu peux consulter, corriger ou supprimer tes données depuis « Moi ». La suppression du compte efface tes données après un délai.\n\n# Lois\n\nRGPD en France, Code du numérique et APDP au Bénin.",
            ),
            "en": (
                "Privacy policy",
                "The data we keep, why, and your rights.",
                "# Data kept\n\nYour number or e-mail, your profile, your orders and appointments, to run the app.\n\n# Your rights\n\nYou can see, correct or delete your data from « Me ». Deleting the account erases your data after a delay.\n\n# Laws\n\nGDPR in France, Digital Code and APDP in Benin.",
            ),
            "sk": (
                "Zásady ochrany súkromia",
                "Údaje, ktoré uchovávame, prečo, a tvoje práva.",
                "# Uchovávané údaje\n\nTvoje číslo alebo e-mail, profil, objednávky a termíny, aby aplikácia fungovala.\n\n# Tvoje práva\n\nSvoje údaje môžeš zobraziť, opraviť alebo vymazať v časti « Ja ». Zrušenie účtu vymaže údaje po určitej lehote.\n\n# Zákony\n\nGDPR vo Francúzsku, Digitálny zákonník a APDP v Benine.",
            ),
        },
    ),
    (
        "mentions-legales",
        "legal",
        {
            "fr": ("Mentions légales", "Qui édite Solange Glow.", "# Éditeur\n\nÀ compléter : société, adresse, numéro d'immatriculation, directeur de la publication.\n\n# Hébergement\n\nÀ compléter : hébergeur et adresse."),
            "en": ("Legal notice", "Who publishes Solange Glow.", "# Publisher\n\nTo fill in: company, address, registration number, publication director.\n\n# Hosting\n\nTo fill in: host and address."),
            "sk": ("Právne informácie", "Kto prevádzkuje Solange Glow.", "# Vydavateľ\n\nDoplniť: spoločnosť, adresa, registračné číslo, zodpovedná osoba.\n\n# Hosting\n\nDoplniť: poskytovateľ a adresa."),
        },
    ),
    (
        "regles-des-jeux",
        "game_rules",
        {
            "fr": (
                "Règles des jeux",
                "Glow Points, roue, quiz et défis : gratuits, sans achat.",
                "# Gratuité\n\nLa roue, les quiz et les défis sont gratuits. Aucun achat n'est demandé pour jouer ou gagner.\n\n# Glow Points\n\nLes points se gagnent selon le barème affiché dans « Mes points », avec des plafonds par jour. Ils n'ont pas de valeur en argent.\n\n# Lots\n\nLes chances de la roue sont affichées et sont les mêmes pour tout le monde.",
            ),
            "en": (
                "Rules of the games",
                "Glow Points, wheel, quiz and challenges: free, no purchase.",
                "# Free\n\nThe wheel, the quizzes and the challenges are free. No purchase is needed to play or win.\n\n# Glow Points\n\nPoints are earned according to the scale shown in « My points », with daily limits. They have no cash value.\n\n# Prizes\n\nThe chances of the wheel are shown and are the same for everyone.",
            ),
            "sk": (
                "Pravidlá hier",
                "Glow Points, koleso, kvíz a výzvy: zadarmo, bez nákupu.",
                "# Zadarmo\n\nKoleso, kvízy a výzvy sú zadarmo. Na hranie ani výhru nie je potrebný nákup.\n\n# Glow Points\n\nBody sa získavajú podľa stupnice v časti « Moje body », s dennými limitmi. Nemajú peňažnú hodnotu.\n\n# Výhry\n\nŠance kolesa sú zobrazené a sú rovnaké pre všetkých.",
            ),
        },
    ),
    (
        "retours-et-remboursements",
        "returns",
        {
            "fr": (
                "Retours et remboursements",
                "Que faire si un produit ne va pas.",
                "# Avant le code de réception\n\nNe donne pas ton code si le produit ne correspond pas : ouvre un litige depuis ta commande.\n\n# Formations\n\nTu as 14 jours pour te rétracter, sauf si tu as demandé l'accès immédiat.\n\n# Qui paie le retour\n\nÀ compléter selon la règle choisie.",
            ),
            "en": (
                "Returns and refunds",
                "What to do if a product is not right.",
                "# Before the receipt code\n\nDo not give your code if the product is not right: open a dispute from your order.\n\n# Courses\n\nYou have 14 days to withdraw, unless you asked for immediate access.\n\n# Who pays the return\n\nTo fill in with the chosen rule.",
            ),
            "sk": (
                "Vrátenie tovaru a peňazí",
                "Čo robiť, ak produkt nie je v poriadku.",
                "# Pred kódom prevzatia\n\nNedávaj svoj kód, ak produkt nezodpovedá: otvor spor zo svojej objednávky.\n\n# Kurzy\n\nMáš 14 dní na odstúpenie, ak si nepožiadala o okamžitý prístup.\n\n# Kto platí vrátenie\n\nDoplniť podľa zvoleného pravidla.",
            ),
        },
    ),
]

FAQ = [
    ("account", {
        "fr": ("Comment créer mon compte ?", "Touche « Moi », puis « Se connecter ». Entre ton numéro ou ton e-mail : tu reçois un code sur WhatsApp, par SMS ou par e-mail."),
        "en": ("How do I create my account?", "Tap « Me », then « Sign in ». Enter your number or e-mail: you get a code by WhatsApp, SMS or e-mail."),
        "sk": ("Ako si vytvorím účet?", "Ťukni na « Ja » a potom « Prihlásiť sa ». Zadaj číslo alebo e-mail: dostaneš kód cez WhatsApp, SMS alebo e-mail."),
    }),
    ("payment", {
        "fr": ("Mon argent est-il protégé ?", "Oui. L'argent reste bloqué jusqu'à ce que tu donnes ton code de réception. S'il y a un problème, ouvre un litige depuis ta commande."),
        "en": ("Is my money protected?", "Yes. The money stays held until you give your receipt code. If there is a problem, open a dispute from your order."),
        "sk": ("Sú moje peniaze chránené?", "Áno. Peniaze sú zablokované, kým nedáš svoj kód prevzatia. Ak je problém, otvor spor zo svojej objednávky."),
    }),
    ("payment", {
        "fr": ("Quand suis-je remboursée ?", "Dès que le litige est décidé ou que la commande est annulée, le remboursement part sur ton moyen de paiement."),
        "en": ("When am I refunded?", "As soon as the dispute is decided or the order is cancelled, the refund goes back to your payment method."),
        "sk": ("Kedy dostanem peniaze späť?", "Hneď ako je spor rozhodnutý alebo objednávka zrušená, peniaze sa vrátia na tvoj spôsob platby."),
    }),
    ("booking", {
        "fr": ("Comment annuler un rendez-vous ?", "Ouvre « Mes rendez-vous », choisis le rendez-vous puis « Annuler ». Les règles d'acompte s'affichent avant."),
        "en": ("How do I cancel an appointment?", "Open « My appointments », choose it, then « Cancel ». The deposit rules are shown first."),
        "sk": ("Ako zruším termín?", "Otvor « Moje termíny », vyber termín a potom « Zrušiť ». Pravidlá zálohy sa zobrazia vopred."),
    }),
    ("shop", {
        "fr": ("Où est ma commande ?", "Ouvre « Mes commandes » : tu vois chaque étape, jusqu'à la remise contre ton code de réception."),
        "en": ("Where is my order?", "Open « My orders »: you see each step, until the hand-over against your receipt code."),
        "sk": ("Kde je moja objednávka?", "Otvor « Moje objednávky »: vidíš každý krok až po odovzdanie za kód prevzatia."),
    }),
    ("selection", {
        "fr": ("Combien de temps pour la Sélection France ?", "Le délai est affiché sur chaque produit : envoi groupé chaque semaine, ou express quand c'est possible."),
        "en": ("How long for the France Selection?", "The delay is shown on each product: grouped shipment every week, or express when possible."),
        "sk": ("Ako dlho trvá France Selection?", "Lehota je uvedená pri každom produkte: skupinové odoslanie každý týždeň alebo expres, keď je to možné."),
    }),
    ("gifts", {
        "fr": ("Comment offrir une prestation depuis la France ?", "Touche « Offrir » sur la vitrine d'une pro, paie en euros, et ta proche reçoit son bon sur WhatsApp."),
        "en": ("How do I offer a service from France?", "Tap « Offer » on a pro's page, pay in euros, and your loved one gets her voucher on WhatsApp."),
        "sk": ("Ako darujem službu z Francúzska?", "Ťukni na « Darovať » na stránke profesionálky, zaplať v eurách a tvoja blízka dostane poukážku cez WhatsApp."),
    }),
    ("pros", {
        "fr": ("Comment devenir pro sur Solange Glow ?", "Dans « Moi », touche « Devenir pro » et remplis ta vitrine. Pour encaisser, ta pièce d'identité est vérifiée."),
        "en": ("How do I become a pro on Solange Glow?", "In « Me », tap « Become a pro » and fill in your page. To be paid, your ID is checked."),
        "sk": ("Ako sa stanem profesionálkou na Solange Glow?", "V časti « Ja » ťukni na « Stať sa profesionálkou » a vyplň svoju stránku. Na prijímanie platieb sa overí tvoj doklad."),
    }),
    ("games", {
        "fr": ("Les jeux sont-ils payants ?", "Non. La roue, le quiz et les défis sont gratuits, sans aucun achat."),
        "en": ("Do the games cost money?", "No. The wheel, the quiz and the challenges are free, with no purchase."),
        "sk": ("Sú hry platené?", "Nie. Koleso, kvíz a výzvy sú zadarmo, bez nákupu."),
    }),
]

EVENT = (
    "help.ticket_answered",
    "L'équipe a répondu à une question envoyée depuis « Nous contacter ».",
    "/aide",
    {
        "fr": ("Réponse à ta question {{ reference }}", "{{ answer }}"),
        "en": ("Answer to your question {{ reference }}", "{{ answer }}"),
        "sk": ("Odpoveď na tvoju otázku {{ reference }}", "{{ answer }}"),
    },
)
ON = {"in_app": True, "push": True, "email": True, "whatsapp": False, "sms": False}


def create(apps, schema_editor):
    Page = apps.get_model("content", "Page")
    for position, (slug, kind, texts) in enumerate(PAGES):
        if Page.objects.filter(slug=slug).exists():
            continue
        values = {"slug": slug, "kind": kind, "position": position}
        for lang, (title, summary, body) in texts.items():
            values[f"title_{lang}"] = title
            values[f"summary_{lang}"] = summary
            values[f"body_{lang}"] = f"{DRAFT[lang]}\n\n{body}"
        values["title"], values["summary"], values["body"] = (
            values["title_fr"],
            values["summary_fr"],
            values["body_fr"],
        )
        Page.objects.create(**values)
    FaqItem = apps.get_model("content", "FaqItem")
    if not FaqItem.objects.exists():
        for position, (topic, texts) in enumerate(FAQ):
            values = {"topic": topic, "position": position}
            for lang, (question, answer) in texts.items():
                values[f"question_{lang}"] = question
                values[f"answer_{lang}"] = answer
            values["question"], values["answer"] = values["question_fr"], values["answer_fr"]
            FaqItem.objects.create(**values)
    Template = apps.get_model("notifications", "NotificationTemplate")
    event_key, description, link, texts = EVENT
    for channel, active in ON.items():
        values = {"description": description, "link": link, "is_active": active}
        for lang, (title, body) in texts.items():
            values[f"title_{lang}"] = title
            values[f"body_{lang}"] = body
        values["title"], values["body"] = values["title_fr"], values["body_fr"]
        Template.objects.get_or_create(event_key=event_key, channel=channel, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
        ("notifications", "0004_contactmessage"),
    ]

    operations = [migrations.RunPython(create, migrations.RunPython.noop)]
