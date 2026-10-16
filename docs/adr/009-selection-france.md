# ADR-009 — Sélection France : la plateforme vend, le prix est calculé

Date : 2026-10-16 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Module 6 du cahier des charges : le propriétaire choisit des produits disponibles en
France ; la cliente au Bénin paie un prix final (transport, douane et frais compris) ;
l'argent est bloqué comme au module 5 ; le propriétaire achète chez le marchand, expédie
(envoi groupé hebdomadaire ou express) et la cliente récupère son colis contre son code.
S'y ajoutent les demandes spéciales (devis) et les précommandes groupées.

## Décision

- **Le vendeur est la plateforme** : un compte « Solange Glow Sélection » (réglage
  `selection.house_email`, créé au premier besoin) est la vendeuse de chaque paiement
  sécurisé (`purpose = "selection"`, `source_type = "selection"`). L'argent arrive dans
  son portefeuille à la remise du colis.
- **Pas de protection acheteur ni de commission** sur ces paiements (règles de prix
  « selection » à 0 %) : le prix calculé est le prix final promis.
- **Formule** (`selection_france/pricing.py`) :
  `[(achat + kg x transport + emballage) x (1 + douane) x (1 + marge) + frais] x 655,957`,
  arrondie à la centaine de FCFA supérieure. Calcul en décimales exactes, résultat entier.
  Paramètres par catégorie (vides : `selection.pricing_defaults`) ; prix enregistrés sur
  le produit et recalculés à la demande (action « Recalculer les prix ») ; prix figé
  dans la commande.
- **Délais affichés** : achat en France, prochain départ hebdomadaire, transit
  (`selection.delays`). Le délai d'envoi du paiement sécurisé (`prep_days`) couvre l'achat
  et l'attente du départ (et la date de fin d'une précommande).
- **Remise** : points de retrait au Bénin (liste dans l'admin), code de réception saisi
  par l'équipe (action de l'admin). Le paiement est « expédié » au départ du lot
  (transporteur et suivi), la commande « prête » à l'arrivée du lot.
- **Un produit par commande** au lancement (avec quantité et choix).
- **Transport aérien** : catégories `air_restricted` (parfums, aérosols) masquées et
  refusées tant que `selection.block_air_restricted` est vrai ; sinon vendues sans
  express.
- **Commandes** réservées aux pays de `selection.countries` (Bénin au lancement), avec
  l'interrupteur « selection ».
- **Précommande groupée** : la cliente paie (argent bloqué) ; objectif atteint → les
  commandes passent « à commander » ; date de fin sans objectif → remboursement
  automatique (Celery Beat, toutes les 15 minutes).

## Conséquences

- Le compte de la plateforme apparaît dans le grand livre comme une vendeuse ; ses
  achats chez les marchands (payés hors de l'appli) ne sont pas dans le grand livre : le
  prix d'achat est gardé sur chaque commande pour le suivi des marges.
- La douane est une estimation : à ajuster par catégorie avec les vrais montants.
- Hors périmètre : pros vendant en France dans cette vitrine (V3), livraison à domicile
  au Bénin, suivi automatique des transporteurs, panier commun avec les boutiques.
