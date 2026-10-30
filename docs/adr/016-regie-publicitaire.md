# ADR-016 — Régie publicitaire et boosts des pros

Date : 2026-10-29 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Le module 12 du cahier des charges décrit une régie intégrée : la plateforme vend elle-même ses
espaces aux marques, aux commerces et aux pros.

- **Emplacements** :
  - bannière de l'accueil ;
  - publication sponsorisée toutes les N publications du fil ;
  - produit sponsorisé ;
  - pro en avant dans la recherche ;
  - écran de lancement.
- **Formats** : image, vidéo courte, carrousel, publication native.
- **Ciblage** : dates, pays, ville, langue, cliente ou pro. Avec aussi une répétition
  maximale par personne et par jour, et une priorité.
- **Statistiques** : affichages, clics, conversions, avec un export pour l'annonceur.
- **Plafond de discrétion** : un nombre maximal de pubs par écran.
- **Bouche-trou** : Google AdSense ou une promo interne.
- **Boosts** : les pros paient pour être mises en avant, à la journée ou à la semaine.

La mention « sponsorisé » doit être visible sur chaque pub (point légal). Le budget JS d'une page
publique est de 230 Ko (ADR-004).

## Décision

- **App `ads`** :
  - `Advertiser` : une marque, un commerce, une pro, ou la plateforme pour ses promos internes ;
  - `Campaign` : vendue, boost ou promo interne. Elle porte les dates, la priorité, le prix
    (forfait ou pour mille affichages), les affichages achetés, le ciblage (pays, villes,
    langues, rôles, métiers) et la répétition par personne et par jour ;
  - `Creative` : le format, les emplacements, le titre, le texte, le bouton, un lien sûr (une
    page de l'appli ou une adresse https), et selon le cas une pro, un produit de boutique ou
    un produit Sélection France ;
  - `CreativeMedia` : les images et vidéos ;
  - `AdStat` : les compteurs par jour, visuel et emplacement ;
  - `AdClick` : les clics, gardés pour trouver les conversions ;
  - `Boost`.
- **Diffusion** (`services/delivery.pick`) :
  - la liste des visuels en cours d'un emplacement est gardée en cache 60 s (réglable),
    sous une version que chaque changement augmente ;
  - le choix se fait en mémoire : dates, ciblage, quota d'affichages, répétition par personne
    et par jour (compteurs dans le cache) ;
  - un tirage pondéré par la priorité garde un seul visuel par campagne ;
  - les campagnes vendues et les boosts passent en premier ; les promos internes ne servent
    que si rien de vendu ne convient (`ads.filler`) ;
  - le plafond par écran est `ads.max_per_screen`.
- **Qui voit** :
  - une personne connectée (pays, ville, langue, rôles, métiers de sa vitrine) ;
  - ou une visiteuse reconnue par un cookie aléatoire `sg_visitor`, posé par le proxy Next,
    sans donnée personnelle ;
  - un pays inconnu n'écarte pas une visiteuse ;
  - aucune pub pour une mineure (`ads.hide_for_minors`, activé). Une date de naissance
    inconnue compte comme mineure ;
  - l'interrupteur « ads » se règle par pays.
- **Mesure, sans script de suivi** :
  - **affichage** : compté quand la pub est envoyée à l'écran. Les pages sont rendues par le
    serveur, donc ça ne coûte aucun JavaScript ;
  - **clic** : un lien signé `/api/v1/ads/click/<jeton>` compte le clic puis redirige ;
  - **conversion** : un paiement (argent payé) ou un rendez-vous sans acompte terminé dans les
    `ads.conversion_days` jours après un clic, une seule fois par clic. Les achats de la
    plateforme (boost, abonnement) ne comptent pas.
- **Écrans** :
  - les pubs sont rendues par le serveur, avec l'étiquette « Sponsorisé par … » (icône et mot)
    et le lien `rel="sponsored"` ;
  - l'écran de lancement est un petit îlot : au plus une fois par jour (stockage du
    navigateur), fermeture automatique et bouton « Passer » dès l'ouverture ;
  - AdSense est un îlot chargé seulement si `ads.filler` le demande et si l'identifiant et le
    bloc sont réglés. Il est coupé au départ : en France, il faut d'abord un bandeau de
    consentement aux cookies.
- **Boosts** :
  - le prix est réglé par pays (`ads.boost_prices`) ;
  - le paiement passe par le module 5 (purpose `boost`, vendu par le compte de la plateforme
    du pays, sans frais de protection) et est versé tout de suite, comme Glow Pro ;
  - une fois payé, une campagne `boost` est créée (pays, ville et métiers de la pro,
    emplacements `ads.boost_placements`) ;
  - la tâche Beat termine les boosts et campagnes échus, et envoie ses chiffres à la pro.
- **Admin** :
  - annonceurs ; campagnes (démarrer et mettre en pause en un clic, aperçu de chaque
    emplacement, export CSV jour par jour pour l'annonceur) ;
  - visuels avec envoi d'images ou de vidéos ;
  - boosts et statistiques en lecture.

## Conséquences

- Les marques paient hors appli (au forfait ou pour mille affichages) ; l'admin note le prix.
- Un affichage compté est une pub envoyée à l'écran, pas forcément vue en entier.
- Seule la première page du fil reçoit des publications sponsorisées. Les pages suivantes,
  chargées par le bouton « Voir plus », n'en ont pas.
- En démo, l'écran de lancement est une campagne en brouillon : actif, il couvrirait tous les
  parcours de test.
- Hors périmètre : AdMob (appli mobile), enchères entre annonceurs, paiement en ligne par les
  marques.
