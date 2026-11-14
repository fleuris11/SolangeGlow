// Screen captures of every route: 360 and 1440 px, light and dark, WebP.
// docker compose run --rm -e LABEL=before -e IDS='<json>' --entrypoint node e2e e2e/capture-screens.mjs
// Result: e2e/screenshots/<LABEL>/<screen>-<width>-<theme>.webp and index.json.
import { mkdirSync, writeFileSync } from "node:fs";

import { chromium } from "@playwright/test";
import sharp from "sharp";

const LABEL = process.env.LABEL ?? "before";
const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const ids = JSON.parse(process.env.IDS ?? "{}");
const ONLY = process.env.ONLY ? new RegExp(process.env.ONLY) : null;
const OUT = `e2e/screenshots/${LABEL}`;
const SIZES = [
  { width: 360, height: 740 },
  { width: 1440, height: 900 },
];
const THEMES = ["light", "dark"];
const QUALITY = 62;
const SETTLE_MS = 1500;
const PRO_PHONE = "+2290196000102";
const API = { "X-SG-Client": "web" };

const screens = {
  anonymous: [
    ["home", "/fr"],
    ["explore", "/fr/explore"],
    ["explore-map", "/fr/explore?view=map"],
    ["showcase", "/fr/aicha"],
    ["showcase-offers", "/fr/aicha/offres"],
    ["booking", "/fr/aicha/rdv"],
    ["shop", "/fr/gloria/shop"],
    ["product", ids.pro && ids.product ? `/fr/${ids.pro}/shop/${ids.product}` : ""],
    ["post", ids.post ? `/fr/p/${ids.post}` : ""],
    ["academy", "/fr/academie"],
    ["course", ids.course ? `/fr/academie/${ids.course}` : ""],
    ["academy-lives", "/fr/academie/lives"],
    ["academy-pass", "/fr/academie/pass"],
    ["selection", "/fr/selection"],
    ["selection-product", ids.selection ? `/fr/selection/${ids.selection}` : ""],
    ["help", "/fr/aide"],
    ["legal", "/fr/pages/conditions-generales"],
    ["auth", "/fr/auth"],
    ["offline", "/fr/hors-ligne"],
    ["gift-offer", "/fr/offrir"],
    ["rankings", "/fr/classements"],
    ["celebrations", "/fr/fetes"],
    ["design", "/fr/design"],
  ],
  client: [
    ["home-signed-in", "/fr"],
    ["following", "/fr/following"],
    ["create", "/fr/create"],
    ["me", "/fr/me"],
    ["me-posts", "/fr/me/posts"],
    ["me-reviews", "/fr/me/reviews"],
    ["saved", "/fr/saved"],
    ["notifications", "/fr/notifications"],
    ["messages", "/fr/messages"],
    ["conversation", ids.conversation ? `/fr/messages/${ids.conversation}` : ""],
    ["calls", "/fr/appels"],
    ["cart", "/fr/cart"],
    ["checkout", "/fr/checkout"],
    ["orders", "/fr/orders"],
    ["order", ids.order ? `/fr/orders/${ids.order}` : ""],
    ["wishlist", "/fr/wishlist"],
    ["payments", "/fr/payments"],
    ["payment", ids.payment ? `/fr/payments/${ids.payment}` : ""],
    ["pay-demo", "/fr/pay/demo"],
    ["appointments", "/fr/appointments"],
    ["selection-orders", "/fr/selection/orders"],
    ["selection-requests", "/fr/selection/requests"],
    ["my-courses", "/fr/academie/mes-formations"],
    ["lesson", ids.course && ids.lesson ? `/fr/academie/${ids.course}/lecon/${ids.lesson}` : ""],
    ["gifts", "/fr/cadeaux"],
    ["points", "/fr/points"],
    ["quiz", "/fr/quiz"],
    ["wheel", "/fr/roue"],
    ["polls", "/fr/choisir"],
    ["poll-new", "/fr/choisir/nouveau"],
    ["challenge", "/fr/defi"],
    ["routine", "/fr/routine"],
    ["welcome", "/fr/welcome"],
  ],
  pro: [
    ["pro-showcase", "/fr/pro"],
    ["pro-services", "/fr/pro/services"],
    ["pro-start", "/fr/pro/start"],
    ["pro-agenda", "/fr/pro/agenda"],
    ["pro-agenda-clients", "/fr/pro/agenda/clients"],
    ["pro-agenda-settings", "/fr/pro/agenda/settings"],
    ["pro-dashboard", "/fr/pro/dashboard"],
    ["pro-shop", "/fr/pro/shop"],
    ["pro-wallet", "/fr/pro/wallet"],
    ["pro-boost", "/fr/pro/boost"],
    ["pro-campaigns", "/fr/pro/campaigns"],
    ["pro-gift-cards", "/fr/pro/gift-cards"],
    ["pro-invoices", "/fr/pro/invoices"],
    ["pro-packages", "/fr/pro/packages"],
    ["pro-plan", "/fr/pro/plan"],
    ["pro-salon", "/fr/pro/salon"],
    ["pro-stock", "/fr/pro/stock"],
    ["pro-academy", "/fr/pro/academy"],
  ],
};

async function signIn(context, phone) {
  const page = await context.newPage();
  await page.goto(`${BASE}/fr/hors-ligne`, { timeout: 180_000 });
  const asked = await page.request.post(`${BASE}/api/v1/auth/otp/request`, {
    data: { phone },
    headers: API,
  });
  const { challenge_id: challenge } = await asked.json();
  let code = "";
  for (let attempt = 0; attempt < 30 && !code; attempt += 1) {
    await page.waitForTimeout(1000);
    const read = await page.request.get(
      `${BASE}/api/v1/dev/last-code?destination=${encodeURIComponent(phone)}`,
    );
    code = read.ok() ? (await read.json()).code : "";
  }
  const verified = await page.request.post(`${BASE}/api/v1/auth/otp/verify`, {
    data: { challenge_id: challenge, code },
    headers: API,
  });
  await page.close();
  return verified.ok();
}

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const index = [];

for (const [who, list] of Object.entries(screens)) {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  let signedIn = who === "anonymous";
  if (who === "client" && ids.client_phone) signedIn = await signIn(context, ids.client_phone);
  if (who === "pro") signedIn = await signIn(context, PRO_PHONE);
  console.log(who, "signed in:", signedIn);
  await context.addInitScript(() => {
    localStorage.setItem("sg.privacy-notice", "1");
    localStorage.setItem("sg.consent", JSON.stringify({ ads: false, at: Date.now(), v: 1 }));
  });
  const page = await context.newPage();
  for (const [name, path] of list) {
    if (ONLY && !ONLY.test(name)) continue;
    if (!path) {
      index.push({ name, path, skipped: "no demo object" });
      continue;
    }
    for (const size of SIZES) {
      for (const theme of THEMES) {
        await page.setViewportSize(size);
        await page.emulateMedia({ colorScheme: theme });
        await page.addInitScript((value) => {
          localStorage.setItem("sg.preferences", JSON.stringify({ theme: value }));
        }, theme);
        const file = `${name}-${size.width}-${theme}.webp`;
        try {
          const answer = await page.goto(`${BASE}${path}`, {
            waitUntil: "load",
            timeout: 240_000,
          });
          await page.waitForTimeout(SETTLE_MS);
          const shot = await page.screenshot({ fullPage: true, type: "png" });
          await sharp(shot, { limitInputPixels: false })
            .webp({ quality: QUALITY })
            .toFile(`${OUT}/${file}`);
          index.push({ who, name, path, file, status: answer?.status(), url: page.url() });
          console.log(answer?.status(), file);
        } catch (error) {
          index.push({ who, name, path, file, error: String(error).slice(0, 200) });
          console.log("ERROR", file, String(error).slice(0, 120));
        }
      }
    }
  }
  await context.close();
}
await browser.close();
writeFileSync(`${OUT}/index.json`, JSON.stringify(index, null, 2));
console.log("done", index.length);
