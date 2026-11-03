# ADR-019 : pile de production

## Contexte

Le projet doit pouvoir être déployé sur un VPS OVH par un propriétaire qui n'est pas développeur.
Il faut une seule machine, peu de comptes externes, un retour arrière simple, et des sauvegardes
restaurables.

## Décisions

- **Caddy** est la seule porte sur Internet : HTTPS automatique, redirection, journaux sans adresse
  IP ni paramètres d'URL. `/api`, `/ws`, `/admin`, `/static` et `/i18n` vont directement à Django ;
  le reste va à Next. Les gros envois et les WebSockets ne passent donc pas par Next.
- **gunicorn + uvicorn-worker** remplacent Daphne en production. Daphne reste une dépendance de
  développement, pour `runserver`.
- **Images construites sur le serveur**, étiquetées par commit. Pas de registre ni de jeton. Les 3
  dernières versions restent sur la machine : `deploy/rollback.sh` y revient en une commande. Il faut
  8 Go de mémoire ou un fichier d'échange.
- **Aucun client ne parle à PostgreSQL ou Redis** : ils sont sur un réseau Docker interne, sans port
  publié (Docker contourne `ufw` pour les ports qu'il publie).
- **Le démarrage échoue plutôt que de tourner mal réglé** (`config/prod_checks.py`) : secrets faibles,
  hôtes vides, adresse sans https, raccourcis de développement. Les expéditeurs Console refusent
  aussi d'exister si le réglage est coupé.
- **`CONN_MAX_AGE = 0`** en production : sous ASGI, chaque requête a son propre fil d'exécution, des
  connexions gardées s'accumuleraient.
- **Un seul client S3 par processus pour signer les liens** (`media/storage.py`) : pour la même raison,
  django-storages construisait un client par requête (0,2 s de processeur), le test de charge l'a montré.
- **Lecture publique par ACL d'objet** (`MEDIA_PUBLIC_ACL=public-read`) : OVH n'a pas de politiques de
  bucket. Le bucket reste privé et sa liste n'est pas lisible. `manage.py setup_storage` règle le CORS
  et prouve les lectures publiques et signées avec les vraies clés.
- **Sauvegardes** dans un conteneur dédié : `pg_dump` chiffré (GPG AES-256, phrase secrète gardée hors
  du serveur), relu avant envoi, rotation jours/semaines/mois ; médias copiés avec rclone, fichiers
  supprimés gardés 30 jours. Un échec remonte à GlitchTip et rend le conteneur `unhealthy`.
- **Le job CI « Production stack »** lance toute la pile avec MinIO et un certificat local : premier
  démarrage, utilisateurs non root, en-têtes, adresses de développement absentes, sauvegarde, effacement,
  restauration, grand livre toujours immuable.

## Conséquences

- Un `NEXT_PUBLIC_*` ou une adresse du site se fixe à la construction : la changer demande
  `./deploy/update.sh --force-build`.
- Quelques secondes de coupure à chaque mise à jour (pas de déploiement sans interruption).
- Un retour arrière ne défait pas les migrations : si la structure a changé de façon incompatible, il
  faut restaurer la sauvegarde faite avant la mise à jour, et perdre ce qui a suivi.
- Le stockage OVH réel, le certificat réel et les appels sur réseau mobile ne se vérifient que sur le
  vrai serveur.
