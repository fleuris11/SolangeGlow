# ADR-020 : pages marketing et animations

## Contexte

Glow v2 veut un rendu spectaculaire, sur de petits Android en 3G. Le budget JavaScript (ADR-004,
230 Ko) est presque plein : 229,5 Ko sur la page de réservation. Le prompt prévoyait GSAP sur les pages
marketing, chargé à la demande, avec un budget séparé contrôlé en CI, et `motion` pour l'interface.

## Décision

**Du CSS d'abord, aucune bibliothèque sur l'accueil public.**

- **Ouverture, halo, éclosion, pression, toasts, feuilles** : CSS (`clip-path`, `transform`, `opacity`,
  jetons de `tokens.css`).
- **Défilement éditorial (parallaxe, jour vers nuit, code)** : CSS `animation-timeline: view()`. Sans
  support du navigateur, la page reste complète et fixe.
- **Choix du métier sur l'accueil** : boutons radio natifs et `:has()`. Pas de script, clavier inclus, et
  une photo non affichée n'est pas téléchargée.
- **Gestes** (feuille glissable, stories, galerie, avant/après) : quelques lignes sans bibliothèque,
  chargées avec l'écran.
- **`motion`** reste disponible à la demande, seulement pour un geste qui l'exige. Aucun écran n'en a
  encore eu besoin.
- **GSAP n'est pas ajouté** pour l'instant : rien de ce que demande la direction ne l'exige. Aucun budget
  séparé n'est donc nécessaire, et l'accueil reste soumis aux 230 Ko de l'ADR-004.

Si une animation marketing venait à exiger GSAP, il serait importé à la demande, après le premier
affichage, avec une entrée dédiée dans `scripts/check-js-budget.mjs`.

## Pourquoi

- Une animation CSS tourne hors du fil principal : elle reste fluide pendant le chargement (`emil-design-eng`).
- GSAP et ScrollTrigger coûteraient plusieurs dizaines de Ko là où le premier affichage compte le plus.
- Tout fonctionne sans JavaScript, ce qui est aussi meilleur pour le SEO et la 3G.

## Limites acceptées

- Safari ancien et certains navigateurs n'ont pas `animation-timeline` : pas de parallaxe chez eux.
- `:has()` manque aux très vieux navigateurs : le premier métier reste affiché et tous les liens marchent.
- La carte qui devient page (`SharedElement`) dépend de `ViewTransition` de React : les navigateurs sans
  View Transitions changent simplement de page. À vérifier écran par écran.

## Vidéos et photos

Vidéos sans son de 8 s et 1,5 Mo au plus, jamais en première image ; aucun téléchargement en économie de
données ni en animations réduites. Photos de démonstration libres, stockées dans le dépôt
(`web/public/media`, crédits dans `CREDITS.md`) ; jamais de lien vers un autre site.
