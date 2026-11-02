#!/bin/sh
# What runs and whether it is healthy, the free disk space, the last backup.
. "$(dirname -- "$0")/lib.sh"

echo "Version : $IMAGE_TAG"
dc ps --format 'table {{.Service}}\t{{.Status}}'
echo
df -h / | tail -n 1 | awk '{print "Disque : " $4 " libres sur " $2}'
echo
printf 'Dernière sauvegarde réussie : '
dc exec -T backup sh -c 'rclone cat "safe:$BACKUP_BUCKET/last-success.txt"' 2>/dev/null || echo "aucune pour l'\''instant"
