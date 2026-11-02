#!/bin/sh
# Database (encrypted) and media to the backup bucket, then rotation.
#   database/daily/, database/weekly/ (Sundays), database/monthly/ (the 1st)
#   media/ (mirror), media-deleted/<date>/ (files removed from the mirror, kept a while)
set -eu
set -o pipefail

SAFE="safe:$BACKUP_BUCKET"
now=$(date -u +%Y-%m-%dT%H%M%SZ)
today=$(date -u +%F)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$GNUPGHOME" && chmod 700 "$GNUPGHOME"

dump="db-$now.dump.gpg"
echo "$now: database"
pg_dump -Fc --no-owner | gpg --batch --yes --pinentry-mode loopback --cipher-algo AES256 \
  --passphrase "$BACKUP_PASSPHRASE" --symmetric -o "$work/$dump"

# A backup that cannot be read back is no backup: checked before it is sent.
gpg --batch --quiet --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" \
  --decrypt "$work/$dump" | pg_restore --list >/dev/null

rclone copyto --s3-no-check-bucket "$work/$dump" "$SAFE/database/daily/$dump"
if [ "$(date -u +%u)" = "7" ]; then
  rclone copyto --s3-no-check-bucket "$work/$dump" "$SAFE/database/weekly/$dump"
fi
if [ "$(date -u +%d)" = "01" ]; then
  rclone copyto --s3-no-check-bucket "$work/$dump" "$SAFE/database/monthly/$dump"
fi

# Keeps the newest files of a folder (names sort by date).
rotate() {
  rclone lsf "$SAFE/database/$1/" | sort -r | tail -n "+$(($2 + 1))" | while read -r old; do
    echo "rotation: $1/$old"
    rclone deletefile "$SAFE/database/$1/$old"
  done
}
rotate daily "$BACKUP_KEEP_DAILY"
rotate weekly "$BACKUP_KEEP_WEEKLY"
rotate monthly "$BACKUP_KEEP_MONTHLY"

echo "$now: media"
rclone sync --s3-no-check-bucket --fast-list "media:$MEDIA_BUCKET" "$SAFE/media" \
  --backup-dir "$SAFE/media-deleted/$today"

limit=$(date -u -d "@$(($(date -u +%s) - BACKUP_MEDIA_DELETED_DAYS * 86400))" +%F)
rclone lsf --dirs-only "$SAFE/media-deleted/" | while read -r folder; do
  day=${folder%/}
  if [ "$day" \< "$limit" ]; then
    echo "rotation: media-deleted/$day"
    rclone purge "$SAFE/media-deleted/$day"
  fi
done

echo "$now" | rclone rcat --s3-no-check-bucket "$SAFE/last-success.txt"
echo "$now: backup done"
