#!/bin/sh
# Puts a backup back: the site stops, the database is replaced, the site restarts.
#   ./deploy/restore.sh latest            the latest backup
#   ./deploy/restore.sh db-....dump.gpg   a given one
#   ./deploy/restore.sh list              what is available
#   add --media to copy the media back too
#   add --yes to skip the question (automated tests)
. "$(dirname -- "$0")/lib.sh"

choice=${1:-}
media=""
yes=""
for option in "${2:-}" "${3:-}"; do
  case "$option" in
    --media) media=--media ;;
    --yes) yes=1 ;;
    "") ;;
    *)
      echo "Option inconnue : $option" >&2
      exit 2
      ;;
  esac
done

if [ -z "$choice" ]; then
  echo "Utilisation : ./deploy/restore.sh latest|list|<nom du fichier> [--media]" >&2
  exit 2
fi

if [ "$choice" = "list" ]; then
  dc exec -T backup sh -c '
    for folder in daily weekly monthly; do
      rclone lsl "safe:$BACKUP_BUCKET/database/$folder/" | sed "s#^#$folder #"
    done
    echo "Dernière sauvegarde réussie :"
    rclone cat "safe:$BACKUP_BUCKET/last-success.txt"'
  exit 0
fi

if [ -z "$yes" ]; then
  echo "ATTENTION : la base actuelle sera remplacée. Tout ce qui a été fait depuis cette sauvegarde sera perdu."
  printf 'Écris OUI pour continuer : '
  read -r answer
  if [ "$answer" != "OUI" ]; then
    echo "Annulé."
    exit 0
  fi
fi

echo "Arrêt du site"
dc stop caddy web backend worker beat

# The failure must not leave the site stopped without saying so.
if ! dc exec -T -e RESTORE_CONFIRM=yes backup restore.sh "$choice" $media; then
  echo "La restauration a échoué. Le site reste arrêté : la base est peut-être incomplète." >&2
  echo "Réessaie avec un autre fichier : ./deploy/restore.sh list" >&2
  exit 1
fi

echo "Redémarrage"
wait_healthy
echo "Restauration terminée."
