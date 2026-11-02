#!/bin/sh
# Runs backup.sh once a day at BACKUP_HOUR_UTC. A failure reaches GlitchTip when it is set up.
set -u

alert() {
  [ -n "${SENTRY_DSN:-}" ] || return 0
  key=$(echo "$SENTRY_DSN" | sed -E 's#^https?://([^@]+)@.*#\1#')
  base=$(echo "$SENTRY_DSN" | sed -E 's#^(https?://)[^@]+@([^/]+)/(.*)$#\1\2/api/\3/store/#')
  curl -s -m 20 -o /dev/null -X POST "$base?sentry_version=7&sentry_key=$key" \
    -H "Content-Type: application/json" \
    -d '{"level":"fatal","logger":"backup","platform":"other","message":"The daily backup failed"}' || true
}

touch /tmp/last-run-ok
while :; do
  now=$(date -u +%s)
  target=$(date -u -d "$(date -u +%F) ${BACKUP_HOUR_UTC}:00:00" +%s)
  if [ "$target" -le "$now" ]; then
    target=$((target + 86400))
  fi
  sleep $((target - now))
  if backup.sh; then
    touch /tmp/last-run-ok
  else
    echo "The backup failed." >&2
    alert
  fi
done
