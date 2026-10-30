import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

/**
 * Ads: a visitor sees the brand banner (always « Sponsored ») and follows it, Aïcha's boost
 * comes first in the search of braids in Cotonou, a sponsored product on the France
 * Selection; Aïcha sees her running boost and its figures. Demo data: seed_demo.
 */
const AICHA = "+2290197000101";
const LOOK = { theme: "light", textSize: "normal" } as const;

async function warmUp(page: Page, path: string) {
  await page.goto(path, { waitUntil: "load", timeout: 300_000 }).catch(() => undefined);
  await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
}

test.use({ viewport: VIEWPORTS.mobile });

test("a visitor sees the sponsored banner, the boosted pro and a sponsored product", async ({
  page,
}) => {
  test.setTimeout(600_000);
  for (const path of ["/fr", "/fr/explore?trade=braids&city=Cotonou", "/fr/selection"]) {
    await warmUp(page, path);
  }
  await page.context().clearCookies();

  await openWith(page, "/fr", LOOK);
  const banner = page.getByRole("complementary", { name: "Publicité" }).first();
  await expect(banner).toBeVisible({ timeout: 120_000 });
  await expect(banner.getByText(/^Sponsorisé par|^Promo Solange Glow/)).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/ads-home.png", fullPage: false });

  await openWith(page, "/fr/explore?trade=braids&city=Cotonou", LOOK);
  const boosted = page.getByRole("link", { name: "Sponsorisé : Aïcha Tresses" });
  await expect(boosted).toBeVisible({ timeout: 120_000 });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/ads-search.png" });
  await boosted.click();
  await expect(page).toHaveURL(/\/fr\/aicha/, { timeout: 120_000 });

  await openWith(page, "/fr/selection", LOOK);
  await expect(page.getByText(/^Sponsorisé par|^Promo Solange Glow/).first()).toBeVisible({
    timeout: 120_000,
  });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/ads-product.png" });
});

test("Aïcha sees her running boost and its figures", async ({ page }) => {
  test.setTimeout(600_000);
  await signInWithPhone(page, AICHA);
  await warmUp(page, "/fr/pro/boost");
  await openWith(page, "/fr/pro/boost", LOOK);
  await expect(page.getByRole("heading", { name: "Booster ma vitrine", level: 1 })).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByText(/Ta vitrine est en tête jusqu'au/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mes boosts" })).toBeVisible();
  await expect(page.getByText(/affichages?$/).first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/ads-boost.png", fullPage: true });
});
