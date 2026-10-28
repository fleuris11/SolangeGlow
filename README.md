# Solange Glow

La plateforme de la beauté et de la mode, au Bénin et en France : annuaire de pros
géolocalisées, réseau social, messagerie, boutiques avec paiement sécurisé (argent bloqué
jusqu'au code de réception), boutique « Sélection France », formations, prise de
rendez-vous et un back-office où tout se règle sans toucher au code.

## Stack

- **Back-end** : Django 5.2 LTS (Python 3.12), Django REST Framework, drf-spectacular,
  GeoDjango + PostgreSQL 16 / PostGIS, Channels, Celery + Celery Beat, Redis, admin Unfold.
- **Web** : Next.js (App Router, TypeScript strict), Tailwind CSS v4, next-intl
  (français, anglais, slovaque), application installable (PWA).
- **Outillage** : Docker Compose, pytest, ruff, pre-commit, ESLint, Prettier, Vitest,
  GitHub Actions.

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS ou Linux).

Rien d'autre à installer : Python, Node.js, PostgreSQL, Redis, MinIO (stockage des
photos et vidéos) et ffmpeg tournent dans les conteneurs. Garde au moins 15 Go libres
sur le disque.

## Lancer le projet en local

```bash
docker compose up --build
```

Le premier démarrage prend quelques minutes. Ensuite :

| Adresse | Contenu |
| --- | --- |
| http://localhost:3000 | Application web |
| http://localhost:8000/admin/ | Back-office |
| http://localhost:8000/api/docs/ | Documentation de l'API |
| http://localhost:8000/api/v1/health | État du serveur |
| http://localhost:3000/fr/design | Catalogue du design system (interne) |
| http://localhost:9001 | Console MinIO (fichiers envoyés) : `solange` / `solange-minio-dev` |

Au démarrage, le back-end applique les migrations et crée les données de base
(pays BJ et FR, devises XOF et EUR, premiers réglages du paiement sécurisé).

Remplir l'application avec des données de démonstration réalistes (30 pros de Cotonou,
Abomey-Calavi, Porto-Novo, Paris et Brest avec prestations, horaires et positions,
clientes, notifications) — en local uniquement :

```bash
docker compose exec backend python manage.py seed_demo
```

Créer un compte administrateur (à faire une fois) :

```bash
docker compose exec backend python manage.py createsuperuser
```

Un fichier `.env` n'est pas obligatoire en local. Pour changer une valeur, copie
`.env.example` en `.env` : chaque variable y est expliquée.

## Tester l'inscription en local

En local, aucun WhatsApp ni SMS n'est envoyé : le code est « envoyé » par le worker
(tâche de fond) et s'affiche dans ses journaux.

1. Ouvre http://localhost:3000/fr/auth (ou « Moi » > « Me connecter ou m'inscrire »).
2. Tape un numéro du Bénin (par exemple `01 97 12 34 56`) ou de France, puis
   « Recevoir mon code ».
3. Dans un terminal, lis le code :

   ```bash
   docker compose logs worker | findstr "One-time code"      # Windows (PowerShell, cmd)
   docker compose logs worker | grep "One-time code"         # macOS, Linux
   ```

   La ligne ressemble à `[DEV] One-time code for +229***56: 482913`.
4. Tape les 6 chiffres : le compte est créé, puis viennent les 3 écrans d'accueil.

Les réglages (durée du code, essais, délai de renvoi, limites, ordre des canaux
WhatsApp puis SMS) sont dans le back-office : Plateforme > Réglages, clés `otp.*`.
Le journal des connexions est dans Comptes > Journal des connexions.

L'âge minimum (16 ans par défaut), ce que les mineurs peuvent faire et le délai avant
l'effacement d'un compte supprimé (30 jours) sont dans les clés `accounts.*`.

## Tester les notifications en local

- Cloche « Alertes » en haut de l'écran, ou http://localhost:3000/fr/notifications.
- « M'envoyer une alerte de test » envoie une notification sur tous les canaux choisis.
- Alertes sur le téléphone (push) : active-les sur cet écran ; elles marchent pour de
  vrai sur http://localhost:3000 (Chrome, Edge, Firefox).
- Les e-mails s'affichent dans les journaux : `docker compose logs worker`.
- Les modèles de messages (fr, en, sk) se modifient dans le back-office :
  Notifications > Modèles de notification. Les heures de silence se règlent avec la clé
  `notifications.quiet_hours`.
- Le journal d'audit (qui a changé quoi) est dans Plateforme > Journal d'audit.

## Tester les pros en local

Après `seed_demo` :

- Explorer : http://localhost:3000/fr/explore — métiers, « Près de moi », filtres
  (ville, ouvert maintenant, à domicile, note, prix), vue « Carte », recherche par mots
  ou à la voix (« tresses à Calavi »).
- Une vitrine : http://localhost:3000/fr/aicha — le lien court http://localhost:3000/aicha
  redirige dans la langue du navigateur.
- Devenir pro : « Moi » > « Devenir pro » (ou http://localhost:3000/fr/pro/start), puis
  « Ma vitrine » (http://localhost:3000/fr/pro) pour tout remplir et publier : infos et
  photos, prestations (durée, temps de pose, options), horaires, réalisations, lieu
  (carte ou GPS, repères écrits et vocaux, vidéo d'itinéraire), déplacement à domicile,
  lien et QR code (image, affiche A4 et stickers en PDF), vérification d'identité.
- Back-office : Pros > Vitrines (filtres, suspension), Pros > Carte des pros,
  Pros > Vérifications d'identité (visible seulement par le groupe « Verification » et
  le super-administrateur ; chaque ouverture d'une pièce est inscrite au journal d'audit).
- Les limites (nombre de prestations, rayon maximum, durée de la vidéo d'itinéraire…),
  la carte (`maps.style_url`, `maps.attribution`, `maps.default_center`) et la recherche
  (`search.*`) se règlent dans Plateforme > Réglages, clés `pros.*`, `maps.*`, `search.*`.

## Tester le réseau social et la modération en local

Après `seed_demo` (publications, stories, commentaires, avis et abonnements de démo) :

- Accueil : http://localhost:3000/fr — stories du jour (anneau autour de l'avatar, badge
  « Libre » pour les créneaux libres) et fil. Connectée, le fil met d'abord les pros
  suivies, puis les tendances de la ville, puis du pays.
- Une publication : http://localhost:3000/fr/p/<id> — commentaires avec réponses,
  partage (WhatsApp, Facebook, TikTok, lien avec aperçu), « Réserver ce look ».
- « Publier » (http://localhost:3000/fr/create) : publication (photo, plusieurs photos,
  vidéo courte, avant/après) ou story (photo/vidéo, texte sur fond, créneaux libres pour
  les pros), en trois étapes avec aperçu ; brouillon ou publication programmée.
- « Moi » > « Mon activité » : mes publications, enregistrés, profils suivis, avis à
  laisser. Les avis ne sont possibles qu'après un rendez-vous ou une commande terminés :
  ils arriveront avec la réservation et la boutique.
- Back-office : Modération > File de modération (Garder / Retirer / Retirer et
  sanctionner en un clic), Sanctions, Signalements ; Réseau social > Publications,
  Commentaires, Stories, Avis.
- Réglages (Plateforme > Réglages) : `social.*` (poids du fil, durée des stories, délai
  de programmation…), `reviews.*`, `moderation.*` (listes de mots, seuil de masquage
  automatique, échelle des sanctions). La vérification par IA reste éteinte tant que
  `MODERATION_AI_URL` est vide.

## Tester la messagerie en local

- Une cliente ouvre une vitrine (par exemple http://localhost:3000/fr/rachida-nails) et
  touche « Écrire » : la conversation s'ouvre (http://localhost:3000/fr/messages/<id>).
  Texte, photo, message vocal (maintenir le micro, ou un simple appui puis « Envoyer »),
  carte d'une publication (bouton « Partager » > « Envoyer en message »), d'une prestation
  ou d'un créneau (pour les pros, sous le champ de saisie).
- La pro se connecte avec son numéro de démo (codes : `docker compose logs worker`) et
  voit la conversation dans « Messages », avec le compteur de non-lus dans le menu.
  « Ma vitrine » > « Messages » : réponses rapides et message d'absence (envoyé hors des
  horaires, une fois par conversation).
- Écrire « Mobile Money », un numéro ou un lien PayPal avant toute commande fait
  apparaître « Paie dans l'appli pour être protégée ».
- Une pro qui écrit à une cliente qui ne la suit pas envoie une demande (onglet
  « Demandes ») ; deux clientes s'écrivent si elles se suivent l'une l'autre.
- Temps réel : `ws://localhost:8000/ws/messaging/` (Channels). Sans connexion temps réel,
  les écrans vérifient les nouveaux messages toutes les 10 secondes ; un message écrit
  hors connexion attend et part dès le retour du réseau.
- Back-office : Messagerie > Conversations signalées / Messages signalés (seulement après
  un signalement ou dans un litige ; chaque ouverture est inscrite au journal d'audit).
- Réglages : `messaging.*` (délai des alertes regroupées, demandes, absence, mots et sites
  de paiement surveillés, longueur, réponses rapides), `throttle.message_send`.
- Appels (préparés, non branchés) : `docker compose --profile calls up livekit`, puis
  `LIVEKIT_URL=ws://localhost:7880`, `LIVEKIT_API_KEY=devkey`, `LIVEKIT_API_SECRET=secret`.

## Tester le paiement sécurisé en local

Avec le prestataire de test (aucun argent réel) :

1. Connecte-toi comme cliente, puis ouvre http://localhost:3000/fr/pay/demo : choisis une
   vitrine (par exemple `gloria`) et un prix, puis « Créer et payer ».
2. Page de paiement de test : « Paiement réussi », « Paiement refusé » ou « J'abandonne ».
   La réponse arrive comme un vrai webhook signé (traité par le worker).
3. La cliente voit son code de réception (6 chiffres) dans « Moi » > « Mes achats et
   ventes ». La vendeuse (numéro de démo, code dans `docker compose logs worker`) voit la
   vente, l'expédie, saisit le code : l'argent passe dans son portefeuille
   (http://localhost:3000/fr/pro/wallet), d'où elle le retire (compte de test).
4. « Un problème avec ma commande » ouvre un litige : argent gelé, salle à trois dans
   « Messages ». La décision se prend dans l'admin.

Back-office, section Finance : tableau de bord par devise (trésorerie, séquestre, dû aux
vendeuses, versements et remboursements en cours, revenus), paiements avec leurs écritures,
litiges (« Verser à la vendeuse », « Rembourser tout », « Rembourser en partie »),
remboursements à faire à la main (FedaPay), versements, grand livre (lecture seule),
rapprochements, règles de commission et de frais, données fiscales DAC7 et exports CSV.
Groupes « Finance » et « Disputes » créés automatiquement.

Réglages : `escrow.*` (délais d'envoi, de versement automatique, de litige, essais du code,
relances), `payments.*` (prestataire par pays, versement minimum, seuil de suspension).
Les délais s'appliquent toutes les 15 minutes (Celery Beat). Les vrais prestataires
s'activent avec leurs clés (`.env.example`) ; le prestataire de test est coupé en
production.

## Tester la boutique en local

Avec les données de démo (`seed_demo`) et le prestataire de test :

1. Ouvre http://localhost:3000/fr/gloria/shop (ou l'onglet « Sa boutique » d'une vitrine) :
   produits avec teintes, vente flash, lots. Sur une fiche produit, choisis une teinte puis
   « Ajouter au panier » (une visiteuse se connecte d'abord, le produit est ajouté ensuite).
2. « Moi » > « Mon panier » > « Commander » : 3 étapes (remise, récapitulatif, paiement).
   Un seul paiement pour toutes les boutiques du panier ; code promo de démo `BIENVENUE`.
3. Page de paiement de test : « Paiement réussi ». Chaque commande a son code de réception.
4. La vendeuse (Gloria, +2290196000102, code dans `docker compose logs worker`) ouvre la
   commande : « Je prépare la commande », puis photo du colis et « Expédier » (ou « C'est
   prêt à retirer »), puis saisit le code : l'argent arrive dans son portefeuille.
5. « Ma boutique » (http://localhost:3000/fr/pro/shop) : produits et stocks, commandes,
   promotions (codes, ventes flash, lots), remise et zones, chiffres. Un produit contenant
   un mot interdit (par exemple « hydroquinone ») est refusé ; un mot « à vérifier »
   l'envoie dans la file de l'admin.

Back-office, section Boutiques : produits à vérifier (accepter, refuser avec une raison,
débloquer), produits, commandes (lecture seule), mots interdits (liste de départ des
dépigmentants à comparer avec la liste officielle de l'ABMed), catégories, promotions.
Groupe « Shop review » créé automatiquement.

Réglages : `shop.*` (photos, panier, remise maximum, ventes flash, alertes de prix, stock
bas) ; interrupteur « shop » par pays dans les feature flags.

## Tester la Sélection France en local

Avec les données de démo (`seed_demo`) et le prestataire de test :

1. Ouvre http://localhost:3000/fr/selection : trois rayons (Petits prix, Tendance, Luxe),
   prix finaux en FCFA, une précommande groupée en cours.
2. Sur une fiche (par exemple « Fond de teint Fenty »), choisis la teinte, l'envoi groupé
   ou l'express (prix et délai affichés), le point de retrait, puis « Payer » : page de
   paiement de test, puis suivi de colis avec le code de réception.
3. Admin, section Sélection France : « Commandes à passer » (lien direct du marchand,
   « Commandé chez le marchand » avec son numéro), « Reçu en France », action « Mettre dans
   un nouveau lot », puis dans le lot : transporteur et suivi, « Lot parti », « Lot
   arrivé », et enfin « Saisir le code de réception » sur la commande.
4. Demande spéciale : http://localhost:3000/fr/selection/requests (lien ou photo). Dans
   l'admin, remplis le prix d'achat, le poids et la catégorie : le calcul s'affiche ;
   « Envoyer le devis ». La cliente de démo Awa (+2290197000201) a déjà un devis.

Le calcul détaillé du prix est sur chaque fiche produit de l'admin ; « Recalculer les
prix » après un changement des paramètres d'une catégorie. Réglages : `selection.*` (taux,
arrondi, paramètres par défaut, délais, pays, devis, blocage des parfums et aérosols).

## Tester les rendez-vous en local

Avec les données de démo (`seed_demo`) :

1. Ouvre http://localhost:3000/fr/bene-coiffure/rdv sans être connectée : choisis
   « Brushing », un créneau, donne un prénom et un numéro : « Demande envoyée » (Béné
   Coiffure confirme chaque demande). Garde le lien « Voir mon rendez-vous ».
2. Connecte-toi comme Bénédicta (+2290196000109) : http://localhost:3000/fr/pro/agenda,
   « 1 demande à confirmer », « Confirmer » (ou « Proposer un autre créneau »).
3. Institut Prisca (+2290197000108) a une équipe de quatre : vue « Jour » par personne,
   « Semaine », glisser un rendez-vous pour le déplacer, toucher une heure libre pour
   ajouter un rendez-vous ou bloquer un moment. « Réglages » : équipe, horaires, règles,
   matériel, dernière minute, lien et QR code, adresse iCal. « Clientes » : fiches.
4. Côté cliente : http://localhost:3000/fr/appointments (Awa, +2290197000201, a un
   rendez-vous demain chez Institut Prisca). Les messages aux invitées (WhatsApp, puis
   SMS) s'affichent dans les journaux du worker.

Les rappels, les demandes sans réponse, la liste d'attente et les groupes avancent seuls
(Celery Beat, toutes les 5 minutes). En développement, `POST /api/v1/dev/booking/time-travel`
(`reference`, `starts_in_minutes`) déplace un rendez-vous dans le temps pour tester ces
étapes. Réglages : `booking.*` (délais, annulation, retard, lapins, rappels, liste
d'attente, groupes) et l'interrupteur « booking » par pays.

## Tester Glow Pro en local

Avec les données de démo (`seed_demo`) :

1. Institut Prisca (+2290197000108) est en Premium : http://localhost:3000/fr/pro/salon
   regroupe les outils (tableau de bord, cartes cadeaux, factures, forfaits, stock,
   campagnes, mon offre). Béné Coiffure (+2290196000109) est en offre gratuite : « Mon
   offre » propose l'essai de 30 jours ; une 3e personne dans l'équipe est refusée tant
   qu'elle n'est pas en Premium.
2. Stock : « Ajouter un produit » (code-barres facultatif), « Scanner » (caméra du
   téléphone, ou code tapé à la main), « Ce que tes prestations utilisent » : le stock
   baisse à chaque rendez-vous terminé.
3. Dans l'agenda, un rendez-vous confirmé ou terminé a un bloc « Encaisser » (espèces ou
   Mobile Money au Bénin, carte cadeau) : le reçu PDF s'ouvre ; « Facture PDF » une fois
   terminé. Toutes les factures : http://localhost:3000/fr/pro/invoices.
4. Cartes cadeaux : sur une vitrine, « Offrir une carte cadeau »
   (http://localhost:3000/fr/institut-prisca/offres), paiement de test ; la pro déduit le
   montant dans « Cartes cadeaux », ou la cliente l'utilise pour payer un acompte.
5. Campagnes : la fiche cliente (« Clientes » dans l'agenda) note l'e-mail, l'anniversaire
   et l'accord pour les offres ; une campagne ne part qu'aux clientes d'accord, avec un
   lien de désinscription (e-mails visibles dans les journaux du backend en dev).
6. Widget : « Réglages » de l'agenda, « Réservation sur ton site » : couleur, adresses
   autorisées, code à copier (`widget.js`).

Réglages : `glowpro.*` (rappel avant échéance, jours de grâce, compte vendeur par pays),
`salon.*` (pays où les espèces sont enregistrables, validité et montants des cartes
cadeaux) ; offres et prix dans l'admin, section Glow Pro. `TERMINAL_PROVIDER` et
`EINVOICE_PROVIDER` restent vides tant que Stripe Terminal et une plateforme de facture
électronique ne sont pas choisis.

## Tester l'Académie en local

Avec les données de démo (`seed_demo`, qui fabrique une vidéo de leçon de 3 minutes) :

1. Catalogue : http://localhost:3000/fr/academie (filtres métier, niveau, langue, prix ;
   fonctionnent sans JavaScript). « Hygiène et sécurité au salon » est gratuite, avec des
   quiz, et donne le badge « Formée sur Solange Glow » ; « Maquillage mariée en 5 étapes »
   (Institut Prisca) coûte 5 000 FCFA ; une formation de Fatou Braids attend la revue.
2. Lecteur : qualité « Économie » d'office en mode économie de données ; « Télécharger
   pour regarder sans réseau », puis couper le réseau : la copie du téléphone est lue.
3. Quiz à la fin de chaque module (bonnes réponses de la démo : « 48 heures », « Après
   chaque cliente ») ; à la fin, « Mes formations » propose le certificat PDF et sa page de
   vérification publique (`/fr/certificat/<code>`, ouverte par le QR code).
4. Achat : la case de renonciation est obligatoire ; paiement de test ; tant qu'aucune
   leçon n'est ouverte, « Me faire rembourser » reste possible 14 jours.
5. Espace formatrice : connecte-toi comme Institut Prisca (+2290197000108) puis
   http://localhost:3000/fr/pro/academy (création en 5 étapes, statistiques, lives).
   La revue se fait dans l'admin, Académie, « Formations à vérifier ».
6. Lives : http://localhost:3000/fr/academie/lives (inscription, salle d'attente, puis
   la salle du live ; voir « Tester les appels et les lives »).

Réglages : `academy.*` (prix plancher et plafond, prix du pass par pays, délai de
remboursement, réussite des quiz, durée des leçons, rappels des lives) ; interrupteurs
« academy » et « lives » par pays.

## Tester les appels et les lives en local

LiveKit (serveur de vidéo) démarre avec le reste (`docker compose up`) ; il partage le
réseau du conteneur `web` : après `docker compose restart web`, lancer aussi
`docker compose restart livekit`. Deux navigateurs (ou une fenêtre privée) suffisent ;
le navigateur demande le micro et la caméra.

1. Appel : connecte-toi comme Awa (+2290197000201), ouvre la vitrine d'Aïcha
   (http://localhost:3000/fr/aicha), « Écrire », puis « Appeler » ou « Vidéo ». Dans
   l'autre navigateur, Aïcha (+2290197000101) voit « Awa t'appelle » : « Décrocher ».
   Après l'appel, la conversation affiche « Appel vidéo, 1 min » ; « Mes appels » est
   dans « Moi ». « Recevoir des appels » se coupe dans les réglages des notifications.
2. Appel à trois : dans l'admin, une salle de litige (Messagerie, Conversations), bouton
   « Appel à trois » ; la cliente et la vendeuse décrochent depuis l'appli.
3. Live de formation : Institut Prisca (+2290197000108) programme un live dans
   « Espace formatrice » ; une élève s'inscrit ; à l'heure (15 min avant au plus tôt),
   « Passer en direct » dans la salle du live. L'élève écrit une question, lève la main ;
   la formatrice donne la parole (le micro de l'élève s'ouvre) puis la reprend.
4. Vente en live : Gloria (+2290196000102), « Ma boutique », onglet « Lives » :
   programmer, ouvrir la salle, « Passer en direct », « Choisir les produits à montrer ».
   Une visiteuse sans compte regarde depuis la boutique ; une cliente « Acheter » : le
   paiement s'ouvre dans un nouvel onglet, le compteur « 1 achat » monte dans le live.
5. Replay : les données de démo en ont deux (Gloria et Prisca). Pour enregistrer un vrai
   live : `LIVEKIT_EGRESS=true` dans `.env`, puis `docker compose --profile replay up -d
   egress` (image lourde, environ 1,5 Go).
6. Faible connexion : avec « Économie de données » dans « Moi », la salle propose tout de
   suite « Audio seul ».

Réglages : `calls.*` (durée, sonnerie, personnes d'un appel de litige), `live.*` (durée,
places, lives gratuits par mois, avance pour passer en direct), `academy.live_replay_days`,
`shop.live_replay_days`, `rtc.token_ttl_seconds` ; limite « lives_per_month » de l'offre
Premium ; interrupteurs « calls », « lives », « live_sales » par pays.

## Client de l'API (web)

Les types du client web sont générés depuis le schéma de l'API. Après toute
modification de l'API côté Django :

```bash
docker compose exec web npm run api:generate     # met à jour src/lib/api/schema.d.ts
```

La CI échoue si ce fichier n'est pas à jour, ou si la première page publique dépasse
230 Ko de JavaScript compressé (`npm run check:js-budget` après `npm run build`).

## Commandes utiles

```bash
# Back-end
docker compose exec backend pytest                         # tests
docker compose exec backend ruff check . && docker compose exec backend ruff format .
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_core     # données de base (sans écraser l'existant)
docker compose exec backend python manage.py seed_demo     # données de démonstration (local uniquement)
docker compose exec backend python manage.py generate_vapid_keys   # clés push pour la production
docker compose exec backend python manage.py makemessages -l fr -l en -l sk --no-location --no-wrap
docker compose exec backend python manage.py compilemessages

# Web
docker compose exec web npm test
docker compose exec web npm run lint
docker compose exec web npm run typecheck
docker compose exec web npm run format
docker compose exec web npm run api:generate               # client API typé depuis le schéma
docker compose run --rm e2e                                # accessibilité (axe) + captures d'écran

# Conteneurs
docker compose logs -f backend worker                      # journaux
docker compose down                                        # arrêter
docker compose down -v                                     # arrêter et effacer la base locale
```

## Structure

```
backend/                Django
  config/               réglages (base, dev, test, prod), urls, asgi, celery
  apps/core/            pays, devises, argent, réglages métier, feature flags,
                        médias (images, vidéos, audio), journal d'audit, fournisseurs externes
  apps/accounts/        comptes (téléphone ou e-mail)
  apps/notifications/   notifications (appli, e-mail, push, WhatsApp, SMS)
  apps/pros/            vitrines des pros, prestations, horaires, recherche, QR codes,
                        vérification d'identité (coffre chiffré)
  apps/social/          publications, fil, commentaires, abonnements, stories, avis vérifiés
  apps/moderation/      signalements, blocages, contenus masqués, file de modération,
                        sanctions
  apps/payments/        paiement sécurisé : grand livre en partie double, séquestre, code de
                        réception, litiges, commissions et frais, portefeuille, prestataires,
                        paiement groupé d'un panier
  apps/shop/            boutiques : produits, variantes et stock, mots interdits, remise et
                        zones, panier, commandes, promotions, liste d'envies et alertes
  apps/selection_france/ Sélection France : catalogue, moteur de prix, commandes vendues par
                        la plateforme, lots d'envoi, demandes spéciales, précommandes groupées
  apps/messaging/       conversations, messages, temps réel (WebSocket), demandes,
                        réponses rapides, message d'absence, anti-fraude, appels audio et
                        vidéo (LiveKit), appel à trois des litiges, journal des appels
  apps/live/            salle de live commune (formations et ventes) : diffusion, questions,
                        mains levées, limites, replay
  assets/fonts/         polices de la marque (OFL) pour les affiches et stickers
  apps/<module>/        un module par grande fonctionnalité
  locale/               traductions (fr, en, sk)
web/                    Next.js
  src/app/[locale]/     pages
  src/components/       composants (ui/, features/)
  src/lib/              API, i18n
  src/messages/         traductions (fr, en, sk)
  src/styles/tokens.css couleurs de la marque
  e2e/                  tests navigateur (Playwright + axe), captures dans e2e/screenshots/
docs/adr/               décisions d'architecture
docker-compose.yml
```

## Règles du projet

- Code, noms et commits en anglais ; tout texte visible est traduisible (fr, en, sk).
- Montants en entiers dans la plus petite unité (`amount_minor`) avec la devise :
  XOF sans décimale, EUR avec deux.
- Délais, commissions et frais se règlent dans le back-office (Plateforme > Réglages),
  jamais dans le code.
- Chaque fonctionnalité arrive avec ses tests.
- Messages de commit au format Conventional Commits.
