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

Rien d'autre à installer : Python, Node.js, PostgreSQL et Redis tournent dans les conteneurs.

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

Au démarrage, le back-end applique les migrations et crée les données de base
(pays BJ et FR, devises XOF et EUR, premiers réglages du paiement sécurisé).

Créer un compte administrateur (à faire une fois) :

```bash
docker compose exec backend python manage.py createsuperuser
```

Un fichier `.env` n'est pas obligatoire en local. Pour changer une valeur, copie
`.env.example` en `.env` : chaque variable y est expliquée.

## Commandes utiles

```bash
# Back-end
docker compose exec backend pytest                         # tests
docker compose exec backend ruff check . && docker compose exec backend ruff format .
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_core     # données de base (sans écraser l'existant)
docker compose exec backend python manage.py makemessages -l fr -l en -l sk --no-location --no-wrap
docker compose exec backend python manage.py compilemessages

# Web
docker compose exec web npm test
docker compose exec web npm run lint
docker compose exec web npm run typecheck
docker compose exec web npm run format
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
  apps/core/            pays, devises, argent, réglages métier, feature flags
  apps/accounts/        comptes (téléphone ou e-mail)
  apps/<module>/        un module par grande fonctionnalité
  locale/               traductions (fr, en, sk)
web/                    Next.js
  src/app/[locale]/     pages
  src/components/       composants (ui/, features/)
  src/lib/              API, i18n
  src/messages/         traductions (fr, en, sk)
  src/styles/tokens.css couleurs de la marque
  e2e/                  tests navigateur (Playwright + axe), captures dans e2e/screenshots/
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
