# ADR-013 — Appels et lives avec LiveKit

Date : 2026-10-28 — Statut : accepté (plan validé par le propriétaire)

## Contexte

Modules 3, 4 et 7 du cahier des charges : appels audio et vidéo dans la messagerie sans
révéler le numéro ; appel à trois dans une salle de litige ; lives de formation (questions
écrites, « lever la main », replay pour les inscrites) ; ventes en live (produits épinglés,
achat sans quitter le live, replay 7 jours). Le live coûte à la minute : durée, nombre de
participants et lives gratuits par mois sont limités et réglables. Mobile d'abord, réseau
3G : un mode audio seul doit être proposé.

## Décision

- **LiveKit** (open source) derrière `apps.core.providers.livekit` : jetons JWT signés par
  le backend (une salle, une identité, ce que la personne peut envoyer : caméra, micro ou
  rien), API serveur Twirp (créer et fermer une salle, donner ou retirer la parole,
  envoyer un événement à la salle, enregistrer l'animatrice), webhooks signés (sha256 du
  corps dans le jeton). Aucune donnée libre n'est envoyée par les téléphones
  (`canPublishData` faux) : questions et mains levées passent par l'API (modération).
  `FakeLiveKit` pour les tests ; sans clés, appels et lives répondent « indisponible ».
- **Appels** dans `messaging` : `Call` + `CallParticipant` ; une conversation à deux
  acceptée des deux côtés, sans blocage, personne qui accepte les appels
  (`User.accept_calls`) ; ou une salle de litige (3 personnes au plus,
  `calls.max_participants`). Sonnerie `calls.ring_seconds`, coupure `calls.max_minutes`
  (Beat chaque minute) ; une ligne `Message.kind = call` écrite dans la conversation
  (traduite à l'affichage). Rien n'est enregistré ; l'admin voit le journal (qui, quand,
  combien de temps) et lance l'appel à trois depuis la salle de litige.
- **Salle de live commune** : app `live` (`LiveRoom`, `LiveQuestion`, `LiveHand`,
  `LiveAttendance`). Chaque module enregistre une *source* (`live.registry`) : `training`
  (Académie, `LiveSession`) et `sale` (boutique, `SaleLive`). La source dit qui anime, qui
  peut regarder (inscrites ; tout le monde pour une vente, même sans compte), qui voit le
  replay et combien de jours ; elle est prévenue au début et à la fin. La salle est créée
  à la première ouverture ; l'animatrice passe en direct à partir de
  `live.start_early_minutes` avant l'heure, le live est coupé après `live.max_minutes`.
- **Temps réel** : chaque changement (question, main, produit épinglé, achat) envoie un
  événement court dans la salle LiveKit ; les écrans rechargent l'état par l'API, et le
  relisent seuls toutes les 10 s en secours.
- **Lives du mois** : `live.free_per_month` (2) pour une pro, formations et ventes
  ensemble ; la limite `lives_per_month` d'une offre Glow Pro la remplace (Premium : 10).
  Les lives de la plateforme ne sont pas limités.
- **Replay** : le service d'enregistrement de LiveKit (egress) enregistre la seule
  animatrice (pas les élèves qui prennent la parole) dès qu'elle publie, directement à la
  place de l'original d'un `MediaAsset` privé (`live_replay`, non envoyable par l'API) ;
  le webhook `egress_ended` lance la chaîne vidéo habituelle (360p et 720p). Le replay
  reste `academy.live_replay_days` (30) ou `shop.live_replay_days` (7) jours, puis le
  fichier est supprimé (Beat chaque nuit).
- **Ventes** : une ligne de panier ajoutée depuis le live garde `sale_live` ; la commande
  aussi ; au paiement reçu, le live compte la commande et son montant (une seule fois) et
  prévient la salle. Le paiement s'ouvre dans un nouvel onglet : le live continue.
- **Faible connexion** : vidéo adaptative et simulcast ; « audio seul » proposé tout de
  suite en économie de données ou en 2G/3G, et après 10 s de qualité mauvaise.
- **Développement** : LiveKit partage le réseau du conteneur `web` (le navigateur de
  Windows et celui des tests e2e l'ouvrent sur `localhost:7880`, médias en UDP 7882 ou TCP
  7881) ; l'enregistrement est en option (profil `replay`, image lourde).

## Conséquences

- Les tests e2e passent de vrais appels entre deux navigateurs (caméra et micro simulés).
- Après `docker compose restart web`, relancer aussi `livekit` (réseau partagé).
- En production : un serveur LiveKit (ou LiveKit Cloud) en `wss://`, un egress avec accès
  au stockage S3, les webhooks vers `/api/v1/livekit/webhook`, des clés propres.
- Hors périmètre : partage d'écran, filtres, sous-titres, lives payants, prix spécial
  pendant un live, enregistrement des appels.
