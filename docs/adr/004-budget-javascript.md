# ADR-004 — Budget JavaScript : 230 Ko compressés

Date : 2026-10-05 — Statut : accepté

## Contexte

La skill front fixait 170 Ko de JavaScript compressé au premier chargement d'une page
publique. Mesure faite sur la version de production : une page presque vide pèse déjà
215 Ko, à cause du socle (React 19, runtime Next.js 16, next-intl, React Query). Le seuil
de 170 Ko n'est pas atteignable sans changer de framework.

## Décision

- Budget révisé : **230 Ko** de JavaScript compressé (gzip) au premier chargement d'une
  page publique pré-rendue (accueil, Messages, Publier, Moi, dans chaque langue).
- Un script (`npm run check:js-budget`) mesure ces pages après `next build` ; la CI
  échoue au-delà du budget.
- Ce qui n'est pas utile au premier affichage est chargé à la demande (`next/dynamic`) :
  feuilles du bas, temps réel des notifications, lecteurs vidéo, éditeurs.

## Conséquences

- Chaque nouvelle dépendance côté client doit être justifiée par sa taille.
- Si le socle grossit (mise à jour majeure), on revoit le budget par un nouvel ADR plutôt
  que de désactiver le contrôle.
