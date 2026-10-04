# ADR-002 — Médias sur un stockage objet compatible S3

Date : 2026-10-05 — Statut : accepté

## Contexte

Les modules à venir manipulent beaucoup de fichiers : photos de profil et de
réalisations, vidéos d'itinéraire et de formations, notes vocales, pièces d'identité.
Les garder sur le disque du serveur rend les sauvegardes, la montée en charge et les
URLs privées difficiles.

## Décision

- Tous les médias vont dans un stockage objet compatible S3, via `django-storages`.
- En local : **MinIO** dans `docker-compose` (bucket créé au démarrage). MinIO ne
  publie plus d'images Docker depuis fin 2025 : on utilise la version communautaire
  `pgsty/minio` (même logiciel, maintenu par le projet Pigsty) et `pgsty/mc`.
- En production : **OVH Object Storage** (S3, hébergé en Europe).
- Un seul bucket, deux préfixes : `public/` (lecture anonyme, ex. photos de profil) et
  `private/` (accès par **URL signée** à durée limitée, ex. pièces d'identité,
  originaux non retraités).
- Chaque fichier passe par le modèle générique `core.media.MediaAsset` et son pipeline
  (vérification du type, réencodage, variantes, suppression des métadonnées).
- En local, les URLs du stockage sont servies à travers le site (`/s3/…`, réécrit par
  Next.js vers MinIO), pour que les URLs signées restent valables.

## Conséquences

- Le code ne manipule jamais de chemin disque : uniquement `MediaAsset` et ses variantes.
- Les tests utilisent un stockage en mémoire.
- Les variables `AWS_*` décrivent le fournisseur ; changer de fournisseur S3 ne demande
  aucun changement de code.
