#!/bin/sh
# Goes back to an earlier version, without touching the data.
#   ./deploy/rollback.sh           the version just before
#   ./deploy/rollback.sh a1b2c3d   a given version
. "$(dirname -- "$0")/lib.sh"

if [ -n "${1:-}" ]; then
  target=$1
else
  target=$(grep -vx "$IMAGE_TAG" "$RELEASE_FILE" | tail -n 1 || true)
fi
if [ -z "$target" ]; then
  echo "Aucune version précédente connue. Versions gardées :" >&2
  docker image ls solangeglow-backend --format '{{.Tag}}' >&2
  exit 2
fi
if ! docker image inspect "solangeglow-backend:$target" >/dev/null 2>&1; then
  echo "La version $target n'est plus sur ce serveur. Versions gardées :" >&2
  docker image ls solangeglow-backend --format '{{.Tag}}' >&2
  exit 3
fi

echo "Retour à la version $target"
IMAGE_TAG=$target
export IMAGE_TAG
wait_healthy
echo "$target" >>"$RELEASE_FILE"
echo "Version $target en ligne."
echo "Si la version retirée avait changé la structure de la base et que des erreurs apparaissent :"
echo "  ./deploy/restore.sh latest  (restaure la sauvegarde faite juste avant la mise à jour)"
