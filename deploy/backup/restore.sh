#!/bin/sh
# Puts a backup back. Called by deploy/restore.sh, which stops the application first.
#   restore.sh latest|<file name> [--media]
# The database is REPLACED. RESTORE_CONFIRM=yes is required.
set -eu
set -o pipefail

SAFE="safe:$BACKUP_BUCKET"
choice=${1:-latest}
with_media=${2:-}

if [ "${RESTORE_CONFIRM:-}" != "yes" ]; then
  echo "RESTORE_CONFIRM=yes is required: the database will be replaced." >&2
  exit 2
fi

find_latest() {
  for folder in daily weekly monthly; do
    rclone lsf "$SAFE/database/$folder/" | sed "s#^#$folder/#"
  done | awk -F/ '{print $2, $0}' | sort -r | head -n 1 | cut -d' ' -f2
}

if [ "$choice" = "latest" ]; then
  path=$(find_latest)
else
  path=""
  for folder in daily weekly monthly; do
    if rclone lsf "$SAFE/database/$folder/" | grep -qx "$choice"; then
      path="$folder/$choice"
      break
    fi
  done
fi
if [ -z "$path" ]; then
  echo "Backup not found: $choice" >&2
  exit 3
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$GNUPGHOME" && chmod 700 "$GNUPGHOME"

echo "Backup: $path"
rclone copyto "$SAFE/database/$path" "$work/backup.gpg"
gpg --batch --quiet --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" \
  --decrypt "$work/backup.gpg" >"$work/backup.dump"
# Refuses a damaged file while the current database is still there.
pg_restore --list "$work/backup.dump" >/dev/null

echo "Replacing the database $PGDATABASE"
psql -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$PGDATABASE\" WITH (FORCE)"
psql -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$PGDATABASE\""
pg_restore --exit-on-error --no-owner -d "$PGDATABASE" "$work/backup.dump"

if [ "$with_media" = "--media" ]; then
  echo "Copying the media back"
  # ACLs are not kept in a copy: public files get theirs back, the rest stays private.
  if [ -n "${MEDIA_PUBLIC_ACL:-}" ]; then
    rclone copy --s3-no-check-bucket --s3-acl "$MEDIA_PUBLIC_ACL" \
      "$SAFE/media/public" "media:$MEDIA_BUCKET/public"
  else
    rclone copy --s3-no-check-bucket "$SAFE/media/public" "media:$MEDIA_BUCKET/public"
  fi
  rclone copy --s3-no-check-bucket --s3-acl private --exclude "/public/**" \
    "$SAFE/media" "media:$MEDIA_BUCKET"
fi
echo "Restore done."
