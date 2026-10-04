# ADR-001 — Le back-office reste l'admin Django Unfold

Date : 2026-10-05 — Statut : accepté

## Contexte

Le cahier des charges v2 proposait un back-office en application Next.js séparée.
Le propriétaire administre seul la plateforme ; chaque écran d'administration en
Next.js demanderait une API dédiée, des permissions par rôle, des formulaires et des
tests en double de ce que l'admin Django fournit déjà. L'admin Unfold est en place :
réglages, feature flags, utilisateurs, journal des connexions, actions groupées.

## Décision

Le back-office reste l'admin Django avec le thème Unfold. Les besoins qui dépassent les
listes et formulaires (tableaux de bord, consoles de modération et de litiges, file de
commandes Sélection France) sont des **pages personnalisées dans l'admin** (vues Django
protégées par les permissions admin, gabarits Unfold), pas une application séparée.

## Conséquences

- Un seul système de permissions (groupes et permissions Django) pour l'équipe.
- Chaque module ajoute son `admin.py` et, si besoin, ses vues dans `admin_views.py`.
- Toute action d'administration est tracée dans le journal d'audit (`core.audit`).
- L'interface d'admin n'est pas « mobile d'abord » : elle vise l'ordinateur.
- La double authentification de l'équipe sera ajoutée dans l'admin (module dédié).
