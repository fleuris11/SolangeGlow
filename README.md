# Solange Glow

La plateforme de la beauté et de la mode, au Bénin et en France : annuaire de pros
géolocalisées, réseau social, messagerie, boutiques avec paiement sécurisé (argent bloqué
jusqu'au code de réception), boutique « Sélection France », formations, prise de
rendez-vous et un back-office où tout se règle sans toucher au code.

## Stack

- **Back-end** : Django 5.2 LTS (Python 3.12), Django REST Framework, drf-spectacular,
  GeoDjango + PostgreSQL 16 / PostGIS, Channels, Celery + Celery Beat, Redis, admin Unfold.
- **Web** : Next.js (App Router, TypeScript strict), Tailwind CSS v4, next-intl
  (français, anglais, slovaque), application installable (PWA).
- **Outillage** : Docker Compose, pytest, ruff, pre-commit, ESLint, Prettier, Vitest,
  GitHub Actions.

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS ou Linux).

Rien d'autre à installer : Python, Node.js, PostgreSQL, Redis, MinIO (stockage des
photos et vidéos) et ffmpeg tournent dans les conteneurs. Garde au moins 15 Go libres
sur le disque.

## Lancer le projet en local

```bash
docker compose up --build
```

Le premier démarrage prend quelques minutes. Ensuite :

| Adresse | Contenu |
| --- | --- |
| http://localhost:3000 | Application web |
| http://localhost:8000/admin/ | Back-office |
| http://localhost:8000/api/docs/ | Documentation de l'API |
| http://localhost:8000/api/v1/health | État du serveur |
| http://localhost:3000/fr/design | Catalogue du design system (interne) |
| http://localhost:9001 | Console MinIO (fichiers envoyés) : `solange` / `solange-minio-dev` |

Au démarrage, le back-end applique les migrations et crée les données de base
(pays BJ et FR, devises XOF et EUR, premiers réglages du paiement sécurisé).

Remplir l'application avec des données de démonstration réalistes (pros de Cotonou,
Abomey-Calavi, Porto-Novo et Paris, clientes, notifications) — en local uniquement :

```bash
docker compose exec backend python manage.py seed_demo
```

Créer un compte administrateur (à faire une fois) :

```bash
docker compose exec backend python manage.py createsuperuser
```

Un fichier `.env` n'est pas obligatoire en local. Pour changer une valeur, copie
`.env.example` en `.env` : chaque variable y est expliquée.

## Tester l'inscription en local

En local, aucun WhatsApp ni SMS n'est envoyé : le code est « envoyé » par le worker
(tâche de fond) et s'affiche dans ses journaux.

1. Ouvre http://localhost:3000/fr/auth (ou « Moi » > « Me connecter ou m'inscrire »).
2. Tape un numéro du Bénin (par exemple `01 97 12 34 56`) ou de France, puis
   « Recevoir mon code ».
3. Dans un terminal, lis le code :

   ```bash
   docker compose logs worker | findstr "One-time code"      # Windows (PowerShell, cmd)
   docker compose logs worker | grep "One-time code"         # macOS, Linux
   ```

   La ligne ressemble à `[DEV] One-time code for +229***56: 482913`.
4. Tape les 6 chiffres : le compte est créé, puis viennent les 3 écrans d'accueil.

Les réglages (durée du code, essais, délai de renvoi, limites, ordre des canaux
WhatsApp puis SMS) sont dans le back-office : Plateforme > Réglages, clés `otp.*`.
Le journal des connexions est dans Comptes > Journal des connexions.

L'âge minimum (16 ans par défaut), ce que les mineurs peuvent faire et le délai avant
l'effacement d'un compte supprimé (30 jours) sont dans les clés `accounts.*`.

## Tester les notifications en local

- Cloche « Alertes » en haut de l'écran, ou http://localhost:3000/fr/notifications.
- « M'envoyer une alerte de test » envoie une notification sur tous les canaux choisis.
- Alertes sur le téléphone (push) : active-les sur cet écran ; elles marchent pour de
  vrai sur http://localhost:3000 (Chrome, Edge, Firefox).
- Les e-mails s'affichent dans les journaux : `docker compose logs worker`.
- Les modèles de messages (fr, en, sk) se modifient dans le back-office :
  Notifications > Modèles de notification. Les heures de silence se règlent avec la clé
  `notifications.quiet_hours`.
- Le journal d'audit (qui a changé quoi) est dans Plateforme > Journal d'audit.

## Client de l'API (web)

Les types du client web sont générés depuis le schéma de l'API. Après toute
modification de l'API côté Django :

```bash
docker compose exec web npm run api:generate     # met à jour src/lib/api/schema.d.ts
```

La CI échoue si ce fichier n'est pas à jour, ou si la première page publique dépasse
230 Ko de JavaScript compressé (`npm run check:js-budget` après `npm run build`).

## Commandes utiles

```bash
# Back-end
docker compose exec backend pytest                         # tests
docker compose exec backend ruff check . && docker compose exec backend ruff format .
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_core     # données de base (sans écraser l'existant)
docker compose exec backend python manage.py seed_demo     # données de démonstration (local uniquement)
docker compose exec backend python manage.py generate_vapid_keys   # clés push pour la production
docker compose exec backend python manage.py makemessages -l fr -l en -l sk --no-location --no-wrap
docker compose exec backend python manage.py compilemessages

# Web
docker compose exec web npm test
docker compose exec web npm run lint
docker compose exec web npm run typecheck
docker compose exec web npm run format
docker compose exec web npm run api:generate               # client API typé depuis le schéma
docker compose run --rm e2e                                # accessibilité (axe) + captures d'écran

# Conteneurs
docker compose logs -f backend worker                      # journaux
docker compose down                                        # arrêter
docker compose down -v                                     # arrêter et effacer la base locale
```

## Structure

```
backend/                Django
  config/               réglages (base, dev, test, prod), urls, asgi, celery
  apps/core/            pays, devises, argent, réglages métier, feature flags,
                        médias (images, vidéos, audio), journal d'audit, fournisseurs externes
  apps/accounts/        comptes (téléphone ou e-mail)
  apps/notifications/   notifications (appli, e-mail, push, WhatsApp, SMS)
  apps/<module>/        un module par grande fonctionnalité
  locale/               traductions (fr, en, sk)
web/                    Next.js
  src/app/[locale]/     pages
  src/components/       composants (ui/, features/)
  src/lib/              API, i18n
  src/messages/         traductions (fr, en, sk)
  src/styles/tokens.css couleurs de la marque
  e2e/                  tests navigateur (Playwright + axe), captures dans e2e/screenshots/
docs/adr/               décisions d'architecture
docker-compose.yml
```

## Règles du projet

- Code, noms et commits en anglais ; tout texte visible est traduisible (fr, en, sk).
- Montants en entiers dans la plus petite unité (`amount_minor`) avec la devise :
  XOF sans décimale, EUR avec deux.
- Délais, commissions et frais se règlent dans le back-office (Plateforme > Réglages),
  jamais dans le code.
- Chaque fonctionnalité arrive avec ses tests.
- Messages de commit au format Conventional Commits.
