"""Words of the platform: never the short « pro ».

We say « professionnel » for the person (« talent » for a while, then the owner chose
« professionnel »), « proposer mes services » for the action and « mon activité » for the
space. Used by migrations on the texts already in the database.
"""

from __future__ import annotations

import re

FRENCH = [
    ("Glow Pro Premium", "Glow Premium"),
    ("Glow Pro", "Glow Premium"),
    ("Menu de mon espace pro", "Menu de mon activité"),
    ("Mon espace pro", "Mon activité"),
    ("Espace pro", "Mon activité"),
    ("d'espace pro", "d'activité"),
    ("espace pro", "activité"),
    ("Tout voir pour les pros", "Tout voir pour proposer mes services"),
    ("Pour les pros", "Proposer mes services"),
    ("Je suis une pro", "Je propose mes services"),
    ("Je suis pro", "Je propose mes services"),
    ("Si tu es pro", "Si tu proposes tes services"),
    ("Tu es pro ?", "Tu proposes tes services ?"),
    ("Devenir pro", "Proposer mes services"),
    ("Rejoins Solange Glow en pro", "Propose tes services sur Solange Glow"),
    ("vitrine de pro", "vitrine"),
    ("Pros vérifiées", "Talents vérifiés"),
    ("Pro vérifiée", "Talent vérifié"),
    ("Pro indépendante", "À mon compte"),
    ("Top Pro", "Top talent"),
    ("Aucune pro", "Aucun talent"),
    ("# pros trouvées", "# talents trouvés"),
    ("# pro trouvée", "# talent trouvé"),
    ("ma pro d'ongles", "un talent pour tes ongles"),
    ("ma pro d'esthétique", "un talent en esthétique"),
    ("ma pro de foulard", "un talent pour ton foulard"),
    ("ma pro de tresses", "un talent pour tes tresses"),
    ("ma pro de coiffure", "un talent en coiffure"),
    ("ma pro de maquillage", "un talent en maquillage"),
    ("ma pro de couture", "un talent en couture"),
    ("Les meilleures pros", "Les meilleurs talents"),
    ("ouvertes en ce moment", "ouverts en ce moment"),
    ("tes préférées", "tes préférés"),
    ("les pros et tes amies", "les talents et tes proches"),
    ("La pro est prévenue", "Le talent est prévenu"),
    ("Elle le scanne", "Il le scanne"),
    ("Si elle demande", "S'il demande"),
    ("à la pro", "au talent"),
    ("à une pro", "à un talent"),
    ("chez la pro", "chez le talent"),
    ("de la pro", "du talent"),
    ("d'une pro", "d'un talent"),
    ("par la pro", "par le talent"),
    ("la pro", "le talent"),
    ("La pro", "Le talent"),
    ("une pro", "un talent"),
    ("Une pro", "Un talent"),
    ("ta pro", "ton talent"),
    ("Ta pro", "Ton talent"),
    ("Cette pro", "Ce talent"),
    ("cette pro", "ce talent"),
    ("pros", "talents"),
    ("Pros", "Talents"),
    ("pro", "talent"),
    ("Pro", "Talent"),
    # Everyone, women and men.
    ("La cliente est prévenue", "Le client est prévenu"),
    ("de la cliente", "du client"),
    ("à la cliente", "au client"),
    ("chez la cliente", "chez le client"),
    ("la cliente", "le client"),
    ("La cliente", "Le client"),
    ("une cliente", "un client"),
    ("Une cliente", "Un client"),
    ("ta cliente", "ton client"),
    ("sa cliente", "son client"),
    ("vraies clientes", "vrais clients"),
    ("clientes", "clients"),
    ("Clientes", "Clients"),
    ("cliente", "client"),
    ("Cliente", "Client"),
]

# Second pass: « talent » became « professionnel » (2026-11-05).
FRENCH_PROFESSIONAL = [
    ("Seule un talent publiée", "Seul un professionnel publié"),
    ("Seule un talent vérifiée", "Seul un professionnel vérifié"),
    ("Seule un talent", "Seul un professionnel"),
    ("le talent est prévenue", "le professionnel est prévenu"),
    ("un talent vérifiée", "un professionnel vérifié"),
    ("talent vérifiée", "professionnel vérifié"),
    ("Top talent", "Top professionnel"),
    ("talents", "professionnels"),
    ("Talents", "Professionnels"),
    ("talent", "professionnel"),
    ("Talent", "Professionnel"),
]

ENGLISH = [
    ("Glow Pro Premium", "Glow Premium"),
    ("Glow Pro", "Glow Premium"),
    ("My pro space menu", "My business menu"),
    ("My pro space", "My business"),
    ("Pro space", "My business"),
    ("See everything for pros", "See how to offer my services"),
    ("For pros", "Offer my services"),
    ("I am a pro", "I offer services"),
    ("Are you a pro?", "Do you offer services?"),
    ("A pro?", "Do you offer services?"),
    ("Verified pro", "Verified talent"),
    ("Independent pro", "On my own"),
    ("Top Pro", "Top talent"),
    ("pros", "talents"),
    ("Pros", "Talents"),
    ("pro", "talent"),
    ("Pro", "Talent"),
]

ENGLISH_PROFESSIONAL = [
    ("Top talent", "Top professional"),
    ("talents", "professionals"),
    ("Talents", "Professionals"),
    ("talent", "professional"),
    ("Talent", "Professional"),
]


def _replace(text: str, rules) -> str:
    for old, new in rules:
        # Never inside a placeholder such as {pro}, {{ pro }} or %(pro)s.
        text = re.sub(rf"(?<![\w{{(]){re.escape(old)}(?![\w}})])(?! *}})", new, text)
    return text


def plain_fr(text: str) -> str:
    return _replace(_replace(text, FRENCH), FRENCH_PROFESSIONAL)


def plain_en(text: str) -> str:
    return _replace(_replace(text, ENGLISH), ENGLISH_PROFESSIONAL)
