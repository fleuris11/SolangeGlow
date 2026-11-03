# Mettre Solange Glow en ligne sur un serveur OVH

Ce guide part d'un serveur vide et va jusqu'au site en ligne. Il ne demande pas d'être
développeur : il faut copier les commandes une par une et vérifier le résultat annoncé.

Compte environ 2 heures, dont une bonne partie d'attente.

**Dans les commandes, remplace toujours :**
- `solangeglow.com` par ton nom de domaine ;
- `moi@exemple.com` par ton adresse e-mail ;
- `IP_DU_SERVEUR` par l'adresse IP de ton serveur.

## Ce qu'il te faut avant de commencer

| Quoi | Où | Pourquoi |
| --- | --- | --- |
| Un serveur VPS sous **Ubuntu 24.04**, avec au moins 4 processeurs (vCore), 8 Go de mémoire et 80 Go de disque | OVH, « VPS » | Fait tourner le site |
| Un **nom de domaine** | OVH, « Noms de domaine », ou un autre vendeur | L'adresse du site |
| Un projet **Public Cloud** avec **2 conteneurs Object Storage (S3)** | OVH, « Public Cloud », « Object Storage » | Les photos et vidéos, et les sauvegardes |
| Un gestionnaire de mots de passe | Bitwarden, 1Password… | Pour garder les clés secrètes hors du serveur |

Les paiements, WhatsApp, SMS, etc. peuvent attendre : le site démarre sans eux. Ils sont
listés dans `docs/checklist-mise-en-ligne.md`. Mais **sans WhatsApp, SMS ni e-mail, personne ne
peut se connecter** : branche au moins l'e-mail (partie 7).

## Partie 1 : préparer le stockage OVH

Dans l'espace client OVH, ouvre ton projet Public Cloud.

1. Va dans **Object Storage**, puis crée un conteneur :
   - type S3 standard, région la plus proche de tes utilisatrices (par exemple `GRA`, Gravelines) ;
   - nom : `solangeglow-media`.
2. Crée un deuxième conteneur, nommé `solangeglow-sauvegardes`. Si possible, choisis une autre
   région : un incendie ne toucherait pas les deux.
3. Va dans **Users & Roles**, crée un utilisateur avec le rôle **ObjectStore operator**.
4. Génère ses clés S3 et note-les : `Access key` et `Secret key`.
5. Note l'adresse du stockage. Elle suit ce modèle : `https://s3.gra.io.cloud.ovh.net`
   (remplace `gra` par ta région).

Garde les conteneurs **privés**. Le site rendra lui-même publiques les seules images prévues pour
cela. Tu le vérifieras à la partie 6.

## Partie 2 : préparer le nom de domaine

Dans la zone DNS du domaine, crée ces enregistrements de type **A**, tous vers `IP_DU_SERVEUR` :

| Nom | Sert à |
| --- | --- |
| (vide, le domaine lui-même) | le site |
| `www` | renvoie vers le site |
| `live` | les appels et les lives |
| `stats` | la mesure d'audience |
| `erreurs` | le suivi des erreurs |

Le changement peut prendre jusqu'à quelques heures. Pour vérifier depuis n'importe quel ordinateur :

```
ping solangeglow.com
```

L'adresse affichée doit être celle du serveur. **Attends que ce soit bon avant la partie 5** : le
certificat HTTPS en a besoin.

## Partie 3 : préparer le serveur

Connecte-toi depuis ton ordinateur (PowerShell sous Windows) :

```
ssh ubuntu@IP_DU_SERVEUR
```

Le mot de passe est dans l'e-mail d'OVH. Puis copie ces blocs un par un.

**Mises à jour du système :**

```
sudo apt update && sudo apt upgrade -y
sudo apt install -y git openssl ufw fail2ban unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades
```

**Docker :**

```
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
```

Déconnecte-toi (`exit`), puis reconnecte-toi avec `ssh`. Vérifie :

```
docker compose version
```

Tu dois voir un numéro de version.

**Pare-feu.** Seuls ces ports restent ouverts : la connexion au serveur, le site, et les appels.

```
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw allow 7881/tcp
sudo ufw allow 7882/udp
sudo ufw --force enable
sudo ufw status
```

Docker sait contourner `ufw` pour les ports qu'il publie : c'est pour cela que la base de données et
Redis ne publient aucun port dans `docker-compose.prod.yml`.

**Mémoire d'appoint.** La construction du site en demande beaucoup d'un coup :

```
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Partie 4 : récupérer le code et créer les secrets

```
sudo mkdir -p /opt/solangeglow
sudo chown ubuntu:ubuntu /opt/solangeglow
git clone https://github.com/fleuris11/SolangeGlow.git /opt/solangeglow
cd /opt/solangeglow
./deploy/generate-secrets.sh solangeglow.com moi@exemple.com
```

Le fichier `.env.prod` est créé, avec des secrets tirés au hasard.

**Tout de suite, recopie deux valeurs dans ton gestionnaire de mots de passe :**

```
grep -E '^(BACKUP_PASSPHRASE|IDENTITY_VAULT_KEY)=' .env.prod
```

- Sans `BACKUP_PASSPHRASE`, les sauvegardes sont illisibles.
- Sans `IDENTITY_VAULT_KEY`, les pièces d'identité des pros sont perdues.

Si le serveur disparaît, ces deux valeurs ne sont nulle part ailleurs. Garde aussi une copie
complète de `.env.prod` au même endroit.

Remplis ensuite le stockage :

```
nano .env.prod
```

Cherche ces lignes avec `Ctrl+W` et complète-les avec ce que tu as noté à la partie 1 :

```
AWS_STORAGE_BUCKET_NAME=solangeglow-media
AWS_S3_ENDPOINT_URL=https://s3.gra.io.cloud.ovh.net
AWS_S3_REGION_NAME=gra
AWS_ACCESS_KEY_ID=ta-access-key
AWS_SECRET_ACCESS_KEY=ta-secret-key
BACKUP_BUCKET=solangeglow-sauvegardes
```

Si le conteneur de sauvegarde est dans une autre région, remplis aussi `BACKUP_S3_ENDPOINT_URL` et
`BACKUP_S3_REGION_NAME`.

Pour enregistrer : `Ctrl+O`, `Entrée`, puis `Ctrl+X`. Chaque variable est expliquée dans le fichier.

## Partie 5 : premier lancement

```
./deploy/first-run.sh moi@exemple.com
```

Cela prend 10 à 20 minutes. Le script construit le site, démarre tout, vérifie le stockage, crée les
données de départ (pays, devises, réglages, métiers, pages légales) et ton compte admin. Aucune donnée
de démonstration n'est créée.

**À la fin, un mot de passe s'affiche une seule fois : note-le.**

S'il s'arrête sur une erreur, l'erreur dit quoi corriger, par exemple :
- `Unsafe production settings` : la ligne citée est à corriger dans `.env.prod` ;
- `A public file cannot be read` : vérifie les clés et la région du stockage.

Corrige, puis relance la même commande : elle peut être relancée sans risque.

## Partie 6 : vérifier que tout marche

```
./deploy/status.sh
```

Chaque service doit afficher `healthy` ou `Up`.

Ensuite, dans ton navigateur :

1. **Le site** : `https://solangeglow.com` affiche l'accueil, avec le cadenas.
2. **L'admin** : `https://solangeglow.com/admin/`.
   - Connecte-toi avec ton e-mail et le mot de passe noté.
   - Configure la double authentification avec une appli (Google Authenticator, par exemple).
   - **Garde les codes de secours.**
   - Le bandeau « À configurer » liste ce qu'il reste à brancher.
3. **Une photo** : une fois connectée sur le site, change ta photo de profil. Elle doit s'afficher.

## Partie 7 : brancher l'e-mail et les outils de suivi

**L'e-mail** (au moins un moyen de connexion). Dans `nano .env.prod`, remplis `EMAIL_HOST`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` et `DEFAULT_FROM_EMAIL`. Puis redémarre avec :

```
./deploy/update.sh --force-build
```

La même commande s'applique après chaque changement de `.env.prod`. La liste complète des services à
brancher est dans `docs/checklist-mise-en-ligne.md`.

**Mesure d'audience (Umami)** :
1. Ouvre `https://stats.solangeglow.com`, connecte-toi avec `admin` / `umami`.
2. **Change ce mot de passe tout de suite.**
3. Ajoute un site, copie son identifiant dans `NEXT_PUBLIC_UMAMI_WEBSITE_ID`.

**Suivi des erreurs (GlitchTip)** :
1. Ouvre `https://erreurs.solangeglow.com`, crée ton compte, une organisation et un projet.
2. Copie le DSN du projet dans `SENTRY_DSN` et `NEXT_PUBLIC_SENTRY_DSN`.
3. Mets `GLITCHTIP_REGISTRATION=false` pour que personne d'autre ne puisse s'inscrire.

Puis lance `./deploy/update.sh --force-build`.

## Mettre à jour le site

```
cd /opt/solangeglow
./deploy/update.sh
```

Le script récupère le code, construit la nouvelle version, fait une sauvegarde, démarre la nouvelle
version et garde les 3 dernières. Le site peut être indisponible quelques secondes pendant le
redémarrage. Choisis un moment calme.

## Revenir en arrière

Si la nouvelle version pose problème :

```
./deploy/rollback.sh
```

Le site revient à la version d'avant, sans toucher aux données. Pour une version précise, donne son
numéro : `./deploy/rollback.sh a1b2c3d`.

**Si des erreurs continuent** après le retour en arrière, la nouvelle version avait sans doute changé
la structure de la base. Restaure alors la sauvegarde faite juste avant la mise à jour (voir ci-dessous).
Ce qui s'est passé sur le site depuis cette sauvegarde sera perdu : commandes et paiements compris.
Note l'heure, et vérifie ensuite les paiements reçus dans les tableaux de bord FedaPay et Stripe.

## Les sauvegardes

**Ce qui se passe tout seul**, chaque nuit à l'heure de `BACKUP_HOUR_UTC` :
- la base de données est chiffrée et envoyée dans le conteneur de sauvegarde ;
- les médias y sont copiés ;
- on garde 7 jours, 4 dimanches et 12 premiers du mois (réglable dans `.env.prod`) ;
- un média supprimé du site reste 30 jours dans la sauvegarde.

**Ce qui n'est pas sauvegardé :** `.env.prod` (garde ta copie à jour), et les statistiques d'Umami et
de GlitchTip, qui ne sont pas indispensables.

| Besoin | Commande |
| --- | --- |
| Sauvegarder maintenant | `./deploy/backup-now.sh` |
| Voir la dernière sauvegarde réussie | `./deploy/status.sh` |
| Voir toutes les sauvegardes | `./deploy/restore.sh list` |
| Restaurer la dernière | `./deploy/restore.sh latest` |
| Restaurer une sauvegarde précise | `./deploy/restore.sh db-2026-11-02T020000Z.dump.gpg` |
| Restaurer aussi les médias | ajoute `--media` à la fin |

La restauration arrête le site, remplace la base, puis redémarre. Elle demande d'écrire `OUI` avant de
commencer. Si le fichier de sauvegarde est abîmé ou si la phrase secrète est fausse, elle s'arrête
avant de toucher à la base.

**Une fois par mois, regarde `./deploy/status.sh`.** Si la dernière sauvegarde a plus d'un jour, c'est
qu'il y a un problème : lis `docker compose --env-file .env.prod -f docker-compose.prod.yml logs backup`.
Une fois GlitchTip branché, un échec de sauvegarde y remonte aussi.

**Si le serveur est perdu :**
1. Prépare un nouveau serveur (parties 3 et 4), mais remets ta copie de `.env.prod` au lieu de lancer
   `generate-secrets.sh`.
2. Lance `./deploy/first-run.sh moi@exemple.com`.
3. Lance `./deploy/restore.sh latest`.
4. Change l'adresse IP dans la zone DNS (partie 2).

## En cas de problème

| Ce que tu vois | Quoi faire |
| --- | --- |
| Le site ne répond plus | `./deploy/status.sh` pour voir le service en cause |
| Un service reste `unhealthy` | `docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=100 <service>` |
| Pas de cadenas, erreur de certificat | Vérifie le DNS (partie 2) et les ports 80 et 443 ; logs du service `caddy` |
| Les appels ne se connectent pas | Vérifie les ports 7881/tcp et 7882/udp, et le nom `live` dans le DNS |
| Disque presque plein | `docker system prune -f` enlève ce qui ne sert plus, sans toucher aux données |
| Personne ne reçoit de code | Bandeau « À configurer » de l'admin : un moyen de connexion manque |

**N'utilise jamais `docker compose down -v`** : cela efface la base de données.

## Ce qui n'a pas pu être essayé avant le vrai serveur

La pile complète (images, HTTPS, démarrage, sauvegarde, restauration) tourne à chaque envoi de code
sur la CI, avec un stockage simulé (MinIO) et un certificat local. Il reste à vérifier une fois sur le
vrai serveur :
- le stockage OVH réel (`first-run.sh` le contrôle pour toi) ;
- le certificat Let's Encrypt réel ;
- une restauration réelle : fais-en une juste après le premier lancement, avant d'ouvrir au public ;
- les appels sur un vrai réseau mobile (voir la checklist) ;
- Lighthouse sur le vrai site : `LH_BASE=https://solangeglow.com`, voir le README.
