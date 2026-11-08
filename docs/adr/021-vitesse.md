# ADR-021 — Vitesse : moins envoyer, plus tôt, une seule fois

Date : 6 novembre 2026. Statut : adopté.

## Contexte

Le propriétaire trouve la plateforme lente. Deux choses différentes se mélangent :

- **En local**, le serveur de développement (Next en mode dev, dans Docker sous Windows, sur 8 Go)
  compile chaque page à sa première visite : plusieurs secondes, parfois une erreur quand la mémoire
  manque. Aucun visiteur ne voit ce mode.
- **En production**, Lighthouse mobile donnait 70/100 sur l'accueil et Explorer (3 novembre). Le
  JavaScript bloquait l'écran 0,3 à 3 s, et chaque page attendait toutes ses données avant d'envoyer
  le moindre octet.

## Ce qui a été mesuré

- Chaque page HTML embarquait **toutes les traductions du site** (161 Ko de texte, fr.json entier),
  même l'accueil d'un visiteur : `NextIntlClientProvider` sans `messages` hérite de tout.
- Dans le fil, chaque publication recopiait ses 7 icônes dessinées dans la description de la page
  envoyée au navigateur.
- L'accueil attendait la plus lente de ses 8 requêtes au serveur avant d'afficher son haut de page, qui
  n'a pourtant besoin d'aucune donnée.
- Aucune page n'avait d'écran de chargement : après un toucher, l'écran restait figé.
- Django recalculait pour chaque visiteur des réponses identiques (fil, recherche, vitrines…).

## Décisions

1. **Traductions par page.** `scripts/client-messages.mjs` suit les imports de chaque page et de chaque
   layout ; sous le premier fichier `"use client"`, il relève les `useTranslations("ns")` et les clés
   écrites en clair (`t("key")`). Il écrit `src/lib/i18n/client-namespaces.json`. Le layout racine
   n'envoie que le socle (`shell`) ; chaque page est enveloppée par `withClientMessages(Page, route)`
   qui n'envoie que ses chemins. Une clé calculée ou un `t` passé à un autre composant font envoyer
   l'espace entier : jamais de texte manquant. La CI vérifie que le fichier est à jour
   (`npm run messages:scope -- --check`). Accueil : 161 Ko → environ 15 Ko de traductions.
2. **Pas d'envoi progressif ni de `loading.tsx`** (essayés puis retirés) : le fil de l'accueil doit
   être dans la page sans script (3G, moteurs de recherche), une adresse inconnue doit répondre 404
   (et non 200 après un squelette), et les copies cachées en attente doublaient les textes. Le cache
   des réponses visiteurs (point 5) rend ces pages rapides sans cela.
3. (retiré, voir 2.)
4. **Objets partagés une fois.** Les icônes des actions d'une publication sont créées au niveau du
   module : React n'écrit qu'une fois un objet réutilisé.
5. **Cache des réponses visiteurs** (`apps/core/api/caching.py`, `VisitorCacheMixin`) : même adresse et
   même langue, même réponse, pendant `performance.visitor_cache_seconds` (60 s, réglable dans
   l'admin, 0 = coupé). Jamais pour une personne connectée, jamais pour une réponse qui lit un cookie,
   l'IP ou l'heure à la seconde (créneaux, publicités comptées). Coupé en développement et en test
   (`VISITOR_CACHE`), pour que ce qui vient de changer se voie tout de suite.
6. **Images** : WebP seulement (l'AVIF, plus léger, faisait attendre 7 s le premier visiteur de chaque taille pendant son encodage), tailles limitées à nos photos (1 600 px), copies gardées un mois ;
   `public/media` et `public/brand` gardés un jour par le navigateur.

## Conséquences

- Toute nouvelle page passe par `withClientMessages` (le script la trouve seul ; la CI échoue si on
  oublie de relancer `npm run messages:scope`).
- Un visiteur peut voir une vitrine vieille d'au plus une minute. Un professionnel connecté voit
  toujours la sienne à jour.
- Les pages « Messages » et « Moi » sont désormais rendues à la demande (elles lisent leurs
  traductions côté serveur) ; le budget JavaScript les mesure comme les autres pages dynamiques.
- Pour juger la vitesse en local, utiliser la version de production (`next start`), jamais le mode dev.
