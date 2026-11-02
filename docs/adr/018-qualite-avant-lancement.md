# ADR-018 — Qualité avant le lancement : accessibilité, SEO, PWA, sécurité, RGPD, suivi

Date : 2026-11-01 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Avant le lancement, il fallait :
- auditer chaque écran avec la check-list de solange-design ;
- finir la voix, le slovaque et le SEO ;
- rendre l'appli installable et utilisable hors ligne ;
- mesurer l'audience sans cookies et suivre les erreurs ;
- durcir la sécurité ;
- mettre en place les documents légaux et les droits RGPD.

Contrainte : le budget JavaScript de l'ADR-004 (230 Ko) est presque atteint.

## Décision

- **Audit** : `e2e/audit.spec.ts` passe les écrans clés à 360 px, en sombre, en très grand texte,
  avec le mode audio. Il vérifie pour chaque écran :
  - aucun défilement de côté ;
  - aucune icône seule (sauf fermer, retour, options) ;
  - le bouton « Écouter » sur les écrans clés ;
  - une seule action principale ;
  - aucune erreur axe grave.

  Il échoue au moindre écart et écrit `audit.json`.
- **Voix** : `DictateButton` (reconnaissance vocale du navigateur, sans bibliothèque, masqué si
  absente). Il est branché dans les avis, les publications, la description d'un produit, les
  repères d'itinéraire et l'aide. Les messages ont déjà les notes vocales.
- **SEO** :
  - plans du site par type (`/sitemap/<type>.xml`), alimentés par `/api/v1/seo/sitemap/<type>`
    (seulement ce qui est public) ;
  - `robots.txt` qui écarte l'admin, l'API et les espaces personnels ;
  - lien canonique et `hreflang` fr/en/sk sur les pages publiques ;
  - Open Graph par défaut ;
  - JSON-LD déjà en place (LocalBusiness, Product, Course).
- **PWA** :
  - écran hors ligne `/[langue]/hors-ligne`, mis en cache à l'installation du service worker et
    servi pour toute page jamais vue ;
  - l'offre d'installation du navigateur est captée par un script intégré à la page (aucun
    fichier JS) ;
  - l'invitation n'apparaît qu'après une commande ou une réservation, ou à partir de la
    3ᵉ visite, puis « Plus tard » la cache 30 jours.
- **Audience** :
  - Umami (sans cookies), dans le profil docker-compose `monitoring`, relayé par l'appli sur
    `/stats` ;
  - événements : inscription, réservation, commande, cadeau.
- **Erreurs** :
  - GlitchTip (compatible Sentry), dans le même profil `monitoring` ;
  - backend : `sentry-sdk`, sans données personnelles (`before_send` masque numéros et
    e-mails, retire l'utilisateur, les cookies et le corps des requêtes) ;
  - web : pas le SDK officiel (environ 70 Ko). À la place, un petit rapporteur au protocole
    Sentry : script intégré côté navigateur, `onRequestError` côté serveur. Il est coupé sans
    DSN et retire les jetons des adresses.
- **Sécurité** :
  - CSP complète posée par `proxy.ts`. Les scripts intégrés restent permis : les pages sont
    statiques, donc pas de nonce par requête ;
  - HSTS en production, Referrer-Policy, Permissions-Policy, COOP ;
  - `pip-audit` et `npm audit` en CI ;
  - filtre de logs qui masque numéros et e-mails ;
  - un test passe chaque adresse d'API qui désigne un objet, connecté ou non : jamais l'objet
    d'un autre (200), jamais d'erreur 500 ;
  - limites de débit : le serveur web transmet l'adresse de la visiteuse avec un secret
    partagé (`INTERNAL_API_TOKEN`). Sans ce secret, toutes les pages rendues par le serveur
    partageraient une seule adresse.
- **RGPD** :
  - case « J'accepte les conditions… » obligatoire à la fin de l'accueil. La date et la
    version de la page des conditions sont gardées sur le compte ;
  - bandeau d'information sur les données, dans le flux de la page (il ne couvre aucun
    bouton), affiché une fois ;
  - « Télécharger mes données » : un ZIP de JSON construit à la demande (le compte et chaque
    ligne qui le désigne, sans secrets), jamais stocké, limité et journalisé.

## Conséquences

- La page du « rdv » est à 229,5 Ko : toute nouvelle fonction partagée par toutes les pages
  doit passer par un script intégré ou un chargement à la demande.
- Umami et GlitchTip ne démarrent qu'avec `--profile monitoring`.
- En production, il faut régler `INTERNAL_API_TOKEN` sur le web et sur Django (même valeur).
- Hors périmètre :
  - nonce CSP (il faudrait rendre toutes les pages dynamiques) ;
  - traduction automatique des contenus ;
  - langues locales (V4).
