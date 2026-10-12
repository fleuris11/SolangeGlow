# ADR-006 — Messagerie en temps réel et appels

Date : 2026-10-12 — Statut : accepté

## Contexte

Le module 3 du cahier des charges demande une messagerie privée (texte, photos, notes
vocales, cartes partagées) qui marche sur un Android d'entrée de gamme en 3G, avec
réception instantanée, « en train d'écrire », accusés « reçu » et « lu », présence, et une
file d'envoi hors ligne. Les appels audio et vidéo arrivent plus tard (V2) et ne doivent
jamais montrer le numéro de téléphone. Les salles de litige à trois (prompt 8) réutilisent
les conversations de groupe. Le contenu des conversations est privé : l'équipe ne le lit
que dans le cadre d'un signalement ou d'un litige.

## Décision

- **Envoi par l'API, le reste par WebSocket.** Un message part par
  `POST /api/v1/conversations/<id>/messages` avec un `client_id` choisi par l'appareil :
  renvoyer le même message (file hors ligne, réseau coupé au mauvais moment) ne crée
  jamais de doublon. Le WebSocket `ws/messaging/` (Channels, un groupe par personne)
  transporte les messages reçus, les accusés, « en train d'écrire », la présence et le
  compteur de non-lus. Une coupure de socket ne perd donc aucun message : l'appareil
  recharge la page de messages à la reconnexion.
- **Accusés par marques de temps** : chaque membre a `delivered_up_to` et `read_up_to`
  (pas une ligne par message et par personne). « Reçu » quand l'appareil confirme la
  réception, « lu » quand la conversation est ouverte à l'écran.
- **Présence dans le cache Redis** : clé « en ligne » rafraîchie toutes les 30 s par
  l'appareil (75 s de grâce), « vu à » gardé 30 jours, compteur d'appareils ouverts pour
  n'annoncer « hors ligne » qu'à la fermeture du dernier. Visible seulement des personnes
  avec qui on a une conversation.
- **Alertes regroupées** : la première alerte d'une conversation est programmée après
  `messaging.notify_delay_seconds` ; les messages arrivés entre-temps sont comptés dans la
  même alerte. Rien si la personne a l'appli ouverte (le compteur en direct suffit) ou si
  elle lit déjà cette conversation.
- **Anti-fraude** : avant toute commande entre les deux personnes (registre
  `fraud.register_trust_check`, que la boutique et les rendez-vous rempliront), les numéros,
  liens de paiement et mots clés (listes dans les réglages) marquent le message et
  affichent « Paie dans l'appli pour être protégée ». Le message est quand même remis.
- **Accès de l'équipe** : l'admin ne liste que les conversations avec un message signalé
  ou de type litige ; chaque ouverture écrit `messaging.conversation_viewed` dans le
  journal d'audit.
- **Appels** : interface `CallProvider` ; implémentation LiveKit (jeton d'accès JWT signé,
  une salle par conversation). Serveur LiveKit de développement dans docker compose
  (profil `calls`, non démarré par défaut). Rien n'est branché côté écrans.

## Conséquences

- Une seule connexion WebSocket par appareil pour la messagerie (en plus de celle des
  notifications) ; elle est ouverte seulement quand la personne est connectée.
- Les photos et notes vocales des messages sont des médias privés : leurs liens signés
  expirent (`media.signed_url_ttl_seconds`) ; l'écran recharge les messages s'il reste
  ouvert longtemps.
- Le jeton d'accès du WebSocket est celui du cookie : après expiration, l'appareil
  rafraîchit sa session puis se reconnecte.
