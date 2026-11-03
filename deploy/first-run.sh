#!/bin/sh
# First start on a new server: images, database, reference data, first admin account.
#   ./deploy/first-run.sh moi@exemple.com
. "$(dirname -- "$0")/lib.sh"

ADMIN_EMAIL=${1:-}
if [ -z "$ADMIN_EMAIL" ]; then
  echo "Utilisation : ./deploy/first-run.sh <e-mail-de-l-admin>" >&2
  exit 2
fi

IMAGE_TAG=$(git rev-parse --short HEAD)
export IMAGE_TAG

echo "1/5 Construction des images (10 à 20 minutes la première fois)"
dc build

# Keys of the push alerts: generated once, they must not change afterwards.
if grep -q '^VAPID_PUBLIC_KEY=$' "$ENV_FILE"; then
  echo "2/5 Clés des notifications push"
  keys=$(dc run --rm --no-deps -T --entrypoint python migrate manage.py generate_vapid_keys 2>/dev/null)
  sed -i '/^VAPID_PUBLIC_KEY=$/d;/^VAPID_PRIVATE_KEY=$/d' "$ENV_FILE"
  echo "$keys" | grep '^VAPID_' >>"$ENV_FILE"
else
  echo "2/5 Clés des notifications push : déjà là"
fi

echo "3/5 Démarrage"
wait_healthy
echo "$IMAGE_TAG" >>"$RELEASE_FILE"

echo "4/5 Vérification du stockage objet"
dc exec -T backend python manage.py setup_storage

echo "5/5 Données de départ et compte admin"
dc exec -T backend python manage.py init_production --admin-email "$ADMIN_EMAIL"

echo
echo "Solange Glow est démarré. Note le mot de passe affiché ci-dessus, il ne sera plus montré."
