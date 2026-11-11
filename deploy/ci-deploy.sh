#!/bin/bash
# The only thing GitHub's deploy key may do on the server: install the latest version of main.
# It is the forced command of that key in ~/.ssh/authorized_keys (docs/deploiement.md):
#   restrict,command="/opt/solangeglow/deploy/ci-deploy.sh" ssh-ed25519 AAAA... github-deploy
# Whatever command GitHub asks for is ignored. One update at a time; everything is logged.
set -euo pipefail

cd /opt/solangeglow
exec 9>/tmp/solangeglow-deploy.lock
if ! flock -n 9; then
  echo "Une mise à jour est déjà en cours : celle-ci est ignorée." >&2
  exit 1
fi

echo "=== $(date -u '+%Y-%m-%d %H:%M:%S UTC') mise à jour lancée par GitHub" >>"$HOME/deploy.log"
./deploy/update.sh 2>&1 | tee -a "$HOME/deploy.log"
