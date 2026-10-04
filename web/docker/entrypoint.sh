#!/bin/sh
# node_modules lives in a Docker volume: reinstall it when package-lock.json changed.
set -e

current=$(sha256sum package-lock.json | cut -d' ' -f1)
installed=$(cat node_modules/.lock-hash 2>/dev/null || true)
if [ "$current" != "$installed" ]; then
  echo "package-lock.json changed: installing dependencies..."
  npm ci
  echo "$current" > node_modules/.lock-hash
fi

exec "$@"
