#!/bin/sh
# Waits for PostgreSQL, then runs the given command.
# With RUN_MIGRATIONS=1 it also applies migrations, compiles translations and seeds
# the reference data (only the main backend service does this).
set -e

python - <<'PY'
import os, sys, time
import psycopg

url = os.environ.get("DATABASE_URL", "")
url = url.replace("postgis://", "postgresql://", 1)
for attempt in range(60):
    try:
        psycopg.connect(url, connect_timeout=2).close()
        break
    except psycopg.OperationalError:
        print("Waiting for the database...", flush=True)
        time.sleep(1)
else:
    sys.exit("Database is not reachable.")
PY

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py compilemessages --ignore=.venv --verbosity 0
  python manage.py seed_core
fi

exec "$@"
