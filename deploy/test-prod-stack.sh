#!/bin/sh
# The production stack, for real, on one machine (CI job "Production stack"):
# images, non-root users, health checks, HTTPS, first start, backup, restore.
#   ./deploy/test-prod-stack.sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

export ENV_FILE=.env.prod.test
export RELEASE_FILE=deploy/.release.test
export COMPOSE_FILES="-f docker-compose.prod.yml -f deploy/compose.test.yml"
export COMPOSE_PROJECT_NAME=solangeglow-prod-test

fail() {
  echo "FAILED: $1" >&2
  exit 1
}

if [ ! -f "$ENV_FILE" ]; then
  ./deploy/generate-secrets.sh localhost ops@example.com
  cat >>"$ENV_FILE" <<EOF
CADDY_GLOBAL_OPTIONS=local_certs
EOF
  sed -i \
    -e 's#^AWS_STORAGE_BUCKET_NAME=$#AWS_STORAGE_BUCKET_NAME=media-test#' \
    -e 's#^AWS_S3_ENDPOINT_URL=$#AWS_S3_ENDPOINT_URL=http://minio:9000#' \
    -e 's#^AWS_S3_REGION_NAME=$#AWS_S3_REGION_NAME=us-east-1#' \
    -e 's#^AWS_ACCESS_KEY_ID=$#AWS_ACCESS_KEY_ID=prodtestkey#' \
    -e 's#^AWS_SECRET_ACCESS_KEY=$#AWS_SECRET_ACCESS_KEY=prodtestsecret#' \
    -e 's#^BACKUP_BUCKET=$#BACKUP_BUCKET=backup-test#' \
    -e 's#^MEDIA_PUBLIC_ACL=.*$#MEDIA_PUBLIC_ACL=#' \
    "$ENV_FILE"
fi

. ./deploy/lib.sh

echo "--- First start (images, stack, storage, reference data, admin)"
WAIT_SECONDS=${WAIT_SECONDS:-900} ./deploy/first-run.sh ops@example.com
IMAGE_TAG=$(tail -n 1 "$RELEASE_FILE")
export IMAGE_TAG
grep -q '^VAPID_PUBLIC_KEY=.' "$ENV_FILE" || fail "no push keys generated"

echo "--- Non-root users"
for service in backend worker beat web backup; do
  user=$(dc exec -T "$service" id -u)
  [ "$user" != "0" ] || fail "$service runs as root"
  echo "$service: uid $user"
done

echo "--- Django deployment checks"
dc exec -T backend python manage.py check --deploy --fail-level WARNING

echo "--- First start again (safe to run again)"
dc exec -T backend python manage.py init_production

echo "--- No demo data"
count=$(dc exec -T backend python manage.py shell -c \
  "from apps.pros.models import ProProfile; print(ProProfile.objects.count())" | tail -n 1)
[ "$count" = "0" ] || fail "demo showcases found: $count"

status() { curl -k -s -o /dev/null -w '%{http_code}' --max-time 60 "$@"; }
check() {
  got=$(status "$2")
  [ "$got" = "$1" ] || fail "$2 answered $got instead of $1"
  echo "$1 $2"
}

echo "--- Through Caddy"
check 200 https://localhost/fr
check 200 https://localhost/en/explore
check 200 https://localhost/robots.txt
check 200 https://localhost/sitemap/pros.xml
check 200 https://localhost/manifest.webmanifest
check 200 "https://localhost/api/v1/health?deep=1"
check 200 https://localhost/api/v1/countries
check 302 https://localhost/admin/
check 200 https://localhost/admin/login/
check 308 http://localhost/fr
check 404 https://localhost/api/docs/
check 404 https://localhost/api/schema/
check 404 https://localhost/api/v1/dev/last-code
check 404 https://localhost/api/v1/dev/payments

echo "--- Security headers"
headers=$(curl -k -s -D - -o /dev/null https://localhost/fr)
for header in strict-transport-security content-security-policy x-content-type-options referrer-policy; do
  echo "$headers" | grep -qi "^$header:" || fail "missing header $header"
  echo "$header"
done
if echo "$headers" | grep -qi '^x-powered-by:'; then fail "x-powered-by is exposed"; fi

echo "--- The admin is static-ready (assets through Django)"
asset=$(curl -k -s https://localhost/admin/login/ | grep -o '/static/[^"]*\.css' | head -n 1)
[ -n "$asset" ] || fail "no stylesheet in the admin"
check 200 "https://localhost$asset"

echo "--- Web socket door (refused without a session, but it is Django that answers)"
ws=$(curl -k -s -o /dev/null -w '%{http_code}' --max-time 10 --http1.1 \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: c29sYW5nZWdsb3cxMjM0NQ==' -H 'Origin: https://localhost' \
  https://localhost/ws/notifications/ || true)
case "$ws" in
  101 | 403) echo "ws answered $ws" ;;
  *) fail "ws answered $ws" ;;
esac

echo "--- Backup and restore"
# A person, a ledger entry and a file: all three must come back.
dc exec -T backend python manage.py shell -c "
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from apps.accounts.models import User
from apps.payments import ledger
User.objects.create_user(email='restore-check@example.com')
cash = ledger.account('provider_cash', 'XOF', provider='restore')
revenue = ledger.account('fee_revenue', 'XOF')
ledger.post('restore_check', 'restore-check', [ledger.debit(cash, 500), ledger.credit(revenue, 500)])
storages['media_private'].save('restore-check.txt', ContentFile(b'keep me'))
"
./deploy/backup-now.sh
./deploy/restore.sh list

dc exec -T backend python manage.py shell -c "
from django.core.files.storage import storages
from apps.accounts.models import User
User.objects.filter(email='restore-check@example.com').delete()
storages['media_private'].delete('restore-check.txt')
"

./deploy/restore.sh latest --media --yes

result=$(dc exec -T backend python manage.py shell -c "
from django.core.files.storage import storages
from django.db import DatabaseError, connection, transaction
from apps.accounts.models import User
from apps.payments.models import JournalEntry, JournalLine
ok_user = User.objects.filter(email='restore-check@example.com').exists()
ok_ledger = JournalEntry.objects.filter(idempotency_key='restore-check').count() == 1
ok_file = storages['media_private'].open('restore-check.txt').read() == b'keep me'
try:
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('UPDATE payments_journalline SET amount_minor = 0')
    ok_trigger = not JournalLine.objects.exists()
except DatabaseError:
    ok_trigger = True
print('RESULT', ok_user, ok_ledger, ok_file, ok_trigger)
" | grep RESULT)
echo "$result"
[ "$result" = "RESULT True True True True" ] || fail "the restore is incomplete"

echo "--- Secrets stay out of the logs"
if dc logs --no-color backend worker beat web 2>&1 | grep -q 'restore-check@example.com'; then
  fail "an e-mail address reached the logs"
fi

echo "--- A wrong passphrase cannot read a backup"
if dc exec -T -e BACKUP_PASSPHRASE=wrong -e RESTORE_CONFIRM=yes backup restore.sh latest 2>/dev/null; then
  fail "a backup was restored with a wrong passphrase"
fi
# The refusal happened before anything was replaced.
check 200 "https://localhost/api/v1/health?deep=1"

echo "--- Production stack: all good"
