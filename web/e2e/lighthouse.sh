#!/bin/sh
# Lighthouse mobile on 5 key pages of a production build served on port 3100
# (README « Mesurer avec Lighthouse »). Run inside the e2e container:
#   docker compose run --rm --entrypoint sh e2e e2e/lighthouse.sh
# LH_CPU: CPU slowdown applied by Lighthouse (4 = phone on a fast computer; 1 on a slow
# computer, whose « benchmarkIndex » is already the one of a phone).
CHROME=$(ls -d /ms-playwright/chromium-*/chrome-linux*/chrome | head -1)
BASE=${LH_BASE:-http://localhost:3100}
CPU=${LH_CPU:-4}
# Chrome started here: on a slow machine, Lighthouse's own launch times out.
"$CHROME" --headless=new --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 \
  about:blank >/dev/null 2>&1 &
sleep 10
for page in "home:/fr" "explore:/fr/explore" "showcase:/fr/aicha" "product:/fr/aicha/shop/bonnet-en-satin" "course:/fr/academie/maquillage-mariee-en-5-etapes"; do
  name=${page%%:*}
  path=${page#*:}
  # Warm the page once: the first answer of the backend is not what is measured.
  node -e "fetch('$BASE$path').then(r=>r.text()).catch(()=>{})"
  npx -y lighthouse@13.6.0 "$BASE$path" --quiet --port=9222 --form-factor=mobile \
    --throttling.cpuSlowdownMultiplier="$CPU" \
    --only-categories=performance,accessibility,seo,best-practices \
    --output=json --output-path="e2e/screenshots/lighthouse-$name.json"
  node -e "const r=require('./e2e/screenshots/lighthouse-$name.json');const c=r.categories;console.log('$name', Object.keys(c).map(k=>k+' '+Math.round(c[k].score*100)).join(', '))" || true
done
