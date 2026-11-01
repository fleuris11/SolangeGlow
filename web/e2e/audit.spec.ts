import AxeBuilder from "@axe-core/playwright";
import { writeFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { signInWithPhone, VIEWPORTS } from "./helpers";

/**
 * Screen by screen audit (solange-design check-list), at 360 px, dark, very large text,
 * audio mode on: no sideways scroll, no icon without a word, the audio button on the key
 * screens, one main action, no serious accessibility issue. Results in
 * e2e/screenshots/audit.json (the « before / after » table of the report).
 */
const AICHA = "+2290197000101";
type Screen = { path: string; speak?: boolean };
type Finding = {
  path: string;
  overflow: number;
  iconOnly: string[];
  speak: boolean | null;
  mainActions: number;
  axe: string[];
};

async function firstPath(page: Page, api: string, pick: (body: never) => string | undefined) {
  const response = await page.request.get(api, { headers: { "X-SG-Client": "web" } });
  return response.ok() ? pick((await response.json()) as never) : undefined;
}

async function inspect(page: Page, screen: Screen): Promise<Finding> {
  await page.goto(screen.path, { waitUntil: "networkidle", timeout: 240_000 });
  await page.evaluate(() => document.fonts.ready);
  // The audio button appears once the page has read the preferences (after hydration).
  if (screen.speak) {
    await page
      .locator('button[aria-label^="Écouter"]')
      .first()
      .waitFor({ timeout: 60_000 })
      .catch(() => undefined);
  }
  const found = await page.evaluate(() => {
    const visible = (el: Element) => {
      const box = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return box.width > 0 && box.height > 0 && style.visibility !== "hidden";
    };
    const controls = [...document.querySelectorAll("main button, main a[href]")].filter(visible);
    // Close and back may stay an icon alone (solange-design).
    const allowed = /fermer|retour|close|back|précédent|suivant|plus d'options|options/i;
    const iconOnly = controls
      .filter((el) => !(el.textContent ?? "").trim() && !el.querySelector("img"))
      .map((el) => el.getAttribute("aria-label") ?? el.outerHTML.slice(0, 80))
      .filter((label) => !allowed.test(label));
    // A chosen filter or tab is coloured too: it is a state, not an action.
    const main = controls.filter(
      (el) =>
        el.className.toString().includes("bg-hibiscus") &&
        !el.getAttribute("aria-current") &&
        el.getAttribute("aria-pressed") !== "true" &&
        el.getAttribute("aria-selected") !== "true",
    );
    return {
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      iconOnly: [...new Set(iconOnly)],
      speak: [...document.querySelectorAll("button")].some((b) =>
        /^Écouter/.test(b.getAttribute("aria-label") ?? b.textContent ?? ""),
      ),
      mainActions: main.length,
    };
  });
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  return {
    path: screen.path,
    ...found,
    speak: screen.speak ? found.speak : null,
    axe: axe.violations
      .filter((v) => ["serious", "critical"].includes(v.impact ?? ""))
      .map((v) => v.id),
  };
}

test.use({ viewport: VIEWPORTS.mobile, colorScheme: "dark" });

test("every key screen passes the check-list at 360 px, dark, very large text, audio", async ({
  page,
}) => {
  test.setTimeout(1_800_000);
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "sg.preferences",
      JSON.stringify({ theme: "dark", textSize: "xlarge", audioMode: true }),
    );
    window.localStorage.setItem("sg.privacy-notice", "1");
  });
  const product = await firstPath(
    page,
    "/api/v1/pros/aicha/shop",
    (b: { products?: { slug: string }[] }) =>
      b.products?.[0] ? `/aicha/shop/${b.products[0].slug}` : undefined,
  );
  const course = await firstPath(
    page,
    "/api/v1/academy/courses",
    (b: { results?: { slug: string }[] }) =>
      b.results?.[0] ? `/academie/${b.results[0].slug}` : undefined,
  );
  const selection = await firstPath(
    page,
    "/api/v1/selection/products",
    (b: { results?: { slug: string }[] }) =>
      b.results?.[0] ? `/selection/${b.results[0].slug}` : undefined,
  );
  const visitor: Screen[] = [
    { path: "/fr", speak: true },
    { path: "/fr/explore", speak: true },
    { path: "/fr/aicha", speak: true },
    { path: "/fr/aicha/shop" },
    ...(product ? [{ path: `/fr${product}`, speak: true }] : []),
    { path: "/fr/aicha/rdv", speak: true },
    { path: "/fr/selection" },
    ...(selection ? [{ path: `/fr${selection}`, speak: true }] : []),
    { path: "/fr/academie" },
    ...(course ? [{ path: `/fr${course}`, speak: true }] : []),
    { path: "/fr/offrir", speak: true },
    { path: "/fr/aide", speak: true },
    { path: "/fr/pages/conditions-generales", speak: true },
    { path: "/fr/auth", speak: true },
    { path: "/fr/hors-ligne", speak: true },
  ];
  const member: Screen[] = [
    { path: "/fr/me" },
    { path: "/fr/cart", speak: true },
    { path: "/fr/orders" },
    { path: "/fr/appointments" },
    { path: "/fr/points", speak: true },
    { path: "/fr/messages" },
    { path: "/fr/notifications" },
    { path: "/fr/cadeaux" },
    { path: "/fr/pro" },
    { path: "/fr/pro/agenda" },
    { path: "/fr/pro/shop" },
  ];

  const findings: Finding[] = [];
  for (const screen of visitor) findings.push(await inspect(page, screen));
  await signInWithPhone(page, AICHA);
  for (const screen of member) findings.push(await inspect(page, screen));
  writeFileSync("e2e/screenshots/audit.json", JSON.stringify(findings, null, 2));

  const failing = findings.filter(
    (f) =>
      f.overflow > 1 || f.iconOnly.length || f.speak === false || f.axe.length || f.mainActions > 1,
  );
  expect(failing, JSON.stringify(failing, null, 2)).toEqual([]);
});
