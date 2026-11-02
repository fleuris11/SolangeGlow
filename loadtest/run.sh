#!/bin/sh
# Load test with growing crowds, on the production image and the local demo data.
#   ./loadtest/run.sh            10, 30 then 60 people at once, 60 seconds each
#   LOADS="10 100" DURATION=120s ./loadtest/run.sh
# Results: loadtest/results/vus-<people>.json
set -eu

cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p results

LOADS=${LOADS:-10 30 60}
DURATION=${DURATION:-60s}
dc() { docker compose -f compose.yml --profile load "$@"; }
# Container on the network of the local stack (docker compose up).
export COMPOSE_PROJECT_NAME=solangeglow

dc build backend-load
dc up -d --no-deps backend-load worker-load
trap 'dc stop backend-load worker-load >/dev/null 2>&1 || true' EXIT

echo "Waiting for the backend"
until dc exec -T backend-load python -c "import urllib.request as u; u.urlopen(u.Request('http://localhost:8000/api/v1/health?deep=1', headers={'Host': 'backend-load'}), timeout=5)" 2>/dev/null; do
  sleep 3
done

dc exec -T backend-load python manage.py shell <prepare.py 2>/dev/null \
  | sed -n 's/^.*LOADDATA//p' >data.json
[ -s data.json ] || { echo "Nothing to test with: is seed_demo done?" >&2; exit 1; }

for vus in $LOADS; do
  echo "--- $vus people at once, $DURATION"
  dc run --rm --no-deps -e VUS="$vus" -e DURATION="$DURATION" k6 run --quiet scenarios.js
done
rm -f data.json
