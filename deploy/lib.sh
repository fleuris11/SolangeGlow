#!/bin/sh
# Shared by the deployment scripts: moves to the project folder and defines `dc`.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

ENV_FILE=${ENV_FILE:-.env.prod}
RELEASE_FILE=${RELEASE_FILE:-deploy/.release}
# Local trials and CI add deploy/compose.test.yml through this variable.
COMPOSE_FILES=${COMPOSE_FILES:--f docker-compose.prod.yml}

if [ ! -f "$ENV_FILE" ]; then
  echo "Le fichier $ENV_FILE n'existe pas. Lance d'abord : ./deploy/generate-secrets.sh" >&2
  exit 1
fi

if [ -z "${IMAGE_TAG:-}" ] && [ -f "$RELEASE_FILE" ]; then
  IMAGE_TAG=$(tail -n 1 "$RELEASE_FILE")
fi
export IMAGE_TAG="${IMAGE_TAG:-latest}"

dc() {
  # shellcheck disable=SC2086
  docker compose --env-file "$ENV_FILE" $COMPOSE_FILES "$@"
}

# Waits for the whole stack, and names what does not start.
wait_healthy() {
  if ! dc up -d --wait --wait-timeout "${WAIT_SECONDS:-600}" "$@"; then
    echo >&2
    echo "Un service n'a pas démarré. État actuel :" >&2
    dc ps >&2
    return 1
  fi
}
