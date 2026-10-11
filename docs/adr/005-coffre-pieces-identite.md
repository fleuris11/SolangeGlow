# ADR-005 — Coffre chiffré pour les pièces d'identité des pros

Date : 2026-10-11 — Statut : accepté

## Contexte

Pour encaisser, une pro envoie une pièce d'identité et un selfie (cahier des charges,
« Les comptes et l'inscription »). Ce sont les données les plus sensibles de la
plateforme. Le cahier des charges demande un stockage séparé et chiffré, un accès réservé
au rôle « vérification » et un journal de chaque consultation. Le pipeline commun des
médias (ADR-002) produit des variantes servies par liens signés : il convient aux photos
privées ordinaires, pas à ces documents.

## Décision

- Les documents ne passent **pas** par `MediaAsset`. Ils vont dans un stockage à part,
  `identity_vault` (préfixe `vault/` du même bucket S3, jamais public, jamais de lien).
- Avant l'envoi au stockage, chaque image est vérifiée (vraie image), débarrassée de ses
  métadonnées (EXIF, GPS), réduite à 2000 px, réencodée en JPEG, puis **chiffrée**
  (Fernet, AES-128 + HMAC) avec une clé dédiée `IDENTITY_VAULT_KEY`.
- Cette clé est distincte de `SECRET_KEY` : la production refuse de démarrer sans elle.
  En développement seulement, une clé est dérivée de `SECRET_KEY`.
- Les images ne sont lues que par une vue de l'admin, qui exige la permission
  `pros.review_identity` (groupe « Verification », créé automatiquement) ; chaque lecture
  écrit `pros.identity_viewed` dans le journal d'audit, avec la personne et l'IP. La
  réponse interdit toute mise en cache.
- La validation (approuver, refuser avec une raison envoyée à la pro) se fait dans la
  file « Vérifications d'identité » de l'admin.

## Conséquences

- Une fuite du bucket seul ne révèle aucun document lisible.
- Perdre `IDENTITY_VAULT_KEY` rend les documents illisibles : elle doit être sauvegardée
  hors du serveur (gestionnaire de mots de passe du propriétaire).
- Changer de clé demandera une commande de rechiffrement (pas encore nécessaire).
- Les autres modules gardent le pipeline commun ; seule la vérification utilise le coffre.
