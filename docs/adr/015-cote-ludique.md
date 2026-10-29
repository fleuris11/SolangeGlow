# ADR-015 — Côté ludique : Glow Points, jeux, niveaux et parrainage

Date : 2026-10-29 — Statut : accepté (le propriétaire a demandé de coder sans attendre
la validation du plan)

## Contexte

Module 10 du cahier des charges. Les clientes doivent avoir une raison d'ouvrir l'appli
chaque jour, même sans acheter :
- Glow Points (connexion, publication, avis, rendez-vous, achat, parrainage), échangés
  contre des réductions ou des formations ;
- série de connexion ;
- « Aide-moi à choisir » ;
- quiz du jour, défi photo de la semaine, roue gratuite ;
- niveaux et badges, classements mensuels des pros, parrainage ;
- « Ma routine » et calendrier des fêtes.

Tout est automatique. Les paramètres se règlent dans l'admin. Les quiz et les thèmes de
défi peuvent être proposés par une IA, puis validés en un clic. Point légal : la roue et
les défis restent gratuits et sans obligation d'achat (sinon c'est une loterie).

## Décision

- **App `gamification`** (titre « Ludique » dans l'admin), une règle par fichier dans
  `services/` : `points`, `streaks`, `quiz`, `wheel`, `polls`, `challenges`, `rewards`,
  `levels`, `rankings`, `referrals`, `routine`, `celebrations`, `hooks`.
- **Grand livre des points** (`PointsEntry`) : une ligne par gain (positif) ou dépense
  (négative), avec une clé unique. Un événement rejoué ne donne rien de plus. Un
  déclencheur PostgreSQL refuse toute modification ou suppression (comme ADR-007). Le
  solde est la somme des lignes. Une correction de l'équipe est une nouvelle ligne
  (« Donner ou reprendre des points », journalisée).
- **Barème et plafonds** :
  - `glow.points` donne les points par action ;
  - `glow.daily_caps` donne le nombre de fois par jour où une action rapporte ;
  - `glow.daily_max_points` est le plafond du jour, hors bonus (`glow.uncapped_actions`).
  - Le jour est celui du pays de la personne (Cotonou ou Paris).
  - Un réglage écrit dans l'admin remplace la valeur du code ; il ne s'y ajoute pas.
- **Points gagnés ailleurs** : un petit bus d'événements commun (`apps/core/events.py`,
  `subscribe` / `emit`, exécuté après le commit, une erreur d'écoute est journalisée sans
  casser l'action d'origine). `social` annonce une publication et un avis, `payments`
  annonce chaque changement de statut (achat compté quand l'argent est versé). Le
  rendez-vous fait passe par le crochet existant `booking.on_completed`. Aucun module
  n'importe le côté ludique.
- **Niveaux des clientes** : Glow, Star, Icône, selon les points gagnés depuis le début
  (`glow.level_thresholds`), jamais selon le solde. Une dépense ne fait donc pas
  redescendre. Avantage : un multiplicateur de points (`glow.level_multipliers`), et des
  récompenses réservées à un niveau.
- **Échange des points** : la plateforme paie toujours la réduction, jamais une pro.
  Les récompenses portent donc sur ce que la plateforme vend :
  - un bon de réduction ou l'express offert sur la Sélection France ;
  - une formation de la plateforme (inscription « Avec les Glow Points »).

  Un bon (`Voucher`) est pris au moment de la commande Sélection France, dans sa
  transaction. La commande garde `discount_xof` et le paiement porte le prix réduit.
  Il reste toujours au moins `glow.voucher_min_to_pay` FCFA à payer. Si la commande
  n'est pas payée ou est remboursée, le bon revient.
- **Roue** :
  - un tour par jour et par personne (contrainte unique) ;
  - jamais payante : aucune route n'existe pour payer un tour ;
  - le tirage se fait sur le serveur (`secrets.SystemRandom`), avec la probabilité
    poids / somme des poids des lots disponibles ;
  - un lot est disponible selon son pays, son stock du jour et l'âge de la personne
    (pas de bon pour une mineure) ;
  - les chances sont affichées en pourcentage ;
  - les tests vérifient la répartition (chi carré sur 20 000 tirages) et l'égalité entre
    les personnes.
- **Quiz et défis** : l'interface `QuizGenerator` (`generators.py`) prépare des brouillons
  à l'avance (7 jours de quiz, 4 semaines de défis) :
  - sans `QUIZ_AI_URL`, ce sont des brouillons vides que l'équipe remplit dans l'admin ;
  - avec la clé, une IA propose des questions et des thèmes.

  Rien n'est en ligne avant « Valider » (un clic). Le défi se clôt le lundi : la photo
  qui a le plus de votes gagne (la plus ancienne en cas d'égalité). La gagnante est
  mise en avant sur l'accueil pendant `games.winner_featured_days`.
- **« Aide-moi à choisir » et défi** :
  - ce sont des contenus modérés (`visibility`, `screen`, signalables : cibles `poll` et
    `challenge_entry`) ;
  - on ne vote pas pour soi ;
  - le défi limite les votes par personne ;
  - le résultat d'un sondage n'est montré qu'après avoir voté, à l'autrice ou à la fin.
- **Pros** :
  - le niveau (`ProProfile.level` : Nouvelle, Confirmée, Top Pro) est calculé chaque
    nuit d'après les prestations et commandes faites, les avis vérifiés, la note et
    l'identité vérifiée (`games.pro_levels`) ;
  - avantages : un badge sur la vitrine et une priorité dans la recherche entre pros
    égales ;
  - les classements mensuels par ville et métier utilisent une moyenne pondérée des avis
    du mois (`games.ranking_prior`, `games.ranking_min_reviews`) : deux avis à 5 étoiles
    ne battent pas quarante avis à 4,8.
- **Parrainage** : un lien personnel `/invite/<code>`. Le code est gardé dans le
  navigateur jusqu'à la création du compte, puis lié (dans les
  `glow.referral_window_days` jours). Les points arrivent au premier achat versé de la
  filleule. La marraine a une limite par mois.
- **Routine et fêtes** : les rappels passent par le hub de notifications, à l'heure
  choisie dans le fuseau de la personne. Le calendrier (`Celebration`) accepte une date
  fixe chaque année ou une date à écrire chaque année (Tabaski, Pâques…).
- **Tâches Beat** :
  - toutes les 15 minutes : rappels de routine et résultats des votes ;
  - chaque matin : brouillons, clôture du défi, niveaux des pros, classement du mois
    écoulé et rappels des fêtes.
- **Interrupteurs** : « games » (tout le module) et « wheel » (la roue seule), par pays.

## Conséquences

- On peut créditer, plafonner et corriger les points sans jamais réécrire l'historique.
- Une réduction offerte par les points ne touche jamais la part d'une pro.
- Une pro ne peut pas financer elle-même une récompense : c'est hors périmètre.
- Pas de récompense « livraison offerte » dans les boutiques des pros, qui paient
  elles-mêmes leur livraison.
- Pas de retrait des points si une publication est retirée par la modération ensuite :
  les plafonds par jour limitent l'abus.
- En démo, le classement du mois en cours est calculé pour que l'écran montre quelque
  chose. En production, seuls les mois terminés sont calculés.
