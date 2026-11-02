#!/bin/sh
# Installs the latest version: backup first, then new images, then restart.
#   ./deploy/update.sh
. "$(dirname -- "$0")/lib.sh"

# git pull may replace this very file: the function is read in full before it runs.
main() {
  KEEP_RELEASES=3
  previous=$IMAGE_TAG

  echo "1/5 Récupération du code"
  git pull --ff-only origin main

  IMAGE_TAG=$(git rev-parse --short HEAD)
  export IMAGE_TAG
  if [ "$IMAGE_TAG" = "$previous" ] && [ "${1:-}" != "--force-build" ]; then
    echo "Déjà à jour ($IMAGE_TAG). Pour reconstruire quand même : ./deploy/update.sh --force-build"
    exit 0
  fi

  echo "2/5 Construction de la version $IMAGE_TAG"
  dc build

  echo "3/5 Sauvegarde avant la mise à jour"
  dc exec -T backup backup.sh

  echo "4/5 Démarrage de la version $IMAGE_TAG"
  if ! wait_healthy; then
    echo "La mise à jour a échoué. Pour revenir à la version d'avant :" >&2
    echo "  ./deploy/rollback.sh $previous" >&2
    exit 1
  fi
  echo "$IMAGE_TAG" >>"$RELEASE_FILE"

  echo "5/5 Nettoyage des anciennes versions (les $KEEP_RELEASES dernières restent)"
  keep=$(tail -n "$KEEP_RELEASES" "$RELEASE_FILE")
  for image in solangeglow-backend solangeglow-web solangeglow-backup; do
    docker image ls "$image" --format '{{.Tag}}' | while read -r tag; do
      case " $(echo "$keep" | tr '\n' ' ') " in
        *" $tag "*) ;;
        *) docker image rm "$image:$tag" >/dev/null 2>&1 || true ;;
      esac
    done
  done

  echo "Version $IMAGE_TAG en ligne."
  echo "En cas de problème : ./deploy/rollback.sh $previous"
}

main "$@"
exit $?
