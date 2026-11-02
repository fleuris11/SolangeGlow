#!/bin/sh
# Creates .env.prod from .env.prod.example and fills every internal secret with random values.
#   ./deploy/generate-secrets.sh solangeglow.com moi@exemple.com
# Never overwrites an existing file: a new key would make existing data unreadable.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

TARGET=${ENV_FILE:-.env.prod}
DOMAIN=${1:-}
ACME_EMAIL=${2:-}

if [ -f "$TARGET" ]; then
  echo "$TARGET existe déjà : rien n'est changé." >&2
  exit 1
fi
if [ -z "$DOMAIN" ] || [ -z "$ACME_EMAIL" ]; then
  echo "Utilisation : ./deploy/generate-secrets.sh <nom-de-domaine> <e-mail>" >&2
  exit 2
fi

long() { openssl rand -hex 32; }

umask 077
cp .env.prod.example "$TARGET"

fill() {
  sed -i "s#^$1=\$#$1=$2#" "$TARGET"
}

fill DOMAIN "$DOMAIN"
fill ACME_EMAIL "$ACME_EMAIL"
fill DJANGO_SECRET_KEY "$(long)"
fill INTERNAL_API_TOKEN "$(long)"
fill POSTGRES_PASSWORD "$(long)"
fill LIVEKIT_API_SECRET "$(long)"
fill BACKUP_PASSPHRASE "$(long)"
fill UMAMI_DB_PASSWORD "$(long)"
fill UMAMI_APP_SECRET "$(long)"
fill GLITCHTIP_DB_PASSWORD "$(long)"
fill GLITCHTIP_SECRET_KEY "$(long)"
# A Fernet key: 32 random bytes in URL-safe base64.
fill IDENTITY_VAULT_KEY "$(openssl rand -base64 32 | tr '+/' '-_')"

echo "$TARGET créé."
echo "À recopier tout de suite hors du serveur (gestionnaire de mots de passe) :"
echo "  BACKUP_PASSPHRASE et IDENTITY_VAULT_KEY. Sans elles, sauvegardes et pièces d'identité sont perdues."
echo "Il te reste à remplir le stockage objet (AWS_*, BACKUP_BUCKET) dans $TARGET."
