import { expect, test } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, VIEWPORTS, type Theme } from "./helpers";

/*
 * Pros (module 1): showcase, short link, Explore list and map.
 * Uses the demo data: `docker compose exec backend python manage.py seed_demo`.
 */

const SIZES = ["mobile", "desktop"] as const;
const THEMES: Theme[] = ["light", "dark"];

for (const size of SIZES) {
  for (const theme of THEMES) {
    test(`showcase ${size} ${theme}`, async ({ page }) => {
      await page.setViewportSize(VIEWPORTS[size]);
      await openWith(page, "/fr/aicha", { theme, textSize: "normal" });
      await expect(page.getByRole("heading", { level: 1, name: "Aïcha Tresses" })).toBeVisible();
      await expectNoSeriousA11yIssue(page);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
      await page.screenshot({
        path: `e2e/screenshots/showcase-${size}-${theme}.png`,
        fullPage: true,
      });
    });
  }
}

test("showcase is ready for search engines", async ({ page }) => {
  await page.goto("/fr/aicha");
  await expect(page).toHaveTitle(/Aïcha Tresses, Tresses à Cotonou/);
  const jsonLd = await page.locator('script[type="application/ld+json"]').textContent();
  const data = JSON.parse(jsonLd ?? "{}");
  expect(data["@type"]).toBe("HairSalon");
  expect(data.address.addressLocality).toBe("Cotonou");
  expect(data.openingHoursSpecification.length).toBeGreaterThan(0);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/fr\/aicha$/);
});

test("short link opens the showcase in the visitor's language", async ({ browser }) => {
  for (const [language, prefix] of [
    ["fr-FR", "fr"],
    ["en-GB", "en"],
  ]) {
    const context = await browser.newContext({ locale: language });
    const page = await context.newPage();
    await page.goto("/aicha");
    await expect(page).toHaveURL(new RegExp(`/${prefix}/aicha$`));
    await context.close();
  }
});

test("unknown pro shows the not found page", async ({ page }) => {
  const response = await page.goto("/fr/personne-inconnue");
  expect(response?.status()).toBe(404);
});

test("very large text on the showcase", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/gloria", { theme: "light", textSize: "xlarge" });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  await page.screenshot({ path: "e2e/screenshots/showcase-mobile-xlarge.png", fullPage: true });
});

for (const size of SIZES) {
  test(`explore list and filters ${size}`, async ({ page }) => {
    await page.setViewportSize(VIEWPORTS[size]);
    await openWith(page, "/fr/explore", { theme: "light", textSize: "normal" });
    await expect(page.getByRole("heading", { name: /pros trouvées/ })).toBeVisible();

    await page
      .getByRole("navigation", { name: "Métiers" })
      .getByRole("link", { name: "Tresses" })
      .click();
    await expect(page).toHaveURL(/trade=braids/);
    await expect(
      page
        .getByRole("region", { name: /pros trouvées/ })
        .getByRole("link", { name: /Aïcha Tresses/ }),
    ).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: `e2e/screenshots/explore-${size}.png`, fullPage: true });

    await page.getByRole("button", { name: /Filtres/ }).click();
    const sheet = page.getByRole("dialog", { name: "Filtres" });
    await sheet.getByRole("button", { name: "Abomey-Calavi" }).click();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: `e2e/screenshots/explore-filters-${size}.png` });
    await sheet.getByRole("button", { name: "Voir les pros" }).click();
    await expect(page).toHaveURL(/city=Abomey-Calavi/);
    const results = page.getByRole("region", { name: /pros trouvées/ });
    await expect(results.getByRole("link", { name: /Fifonsi Tresses/ })).toBeVisible();
    await expect(results.getByRole("link", { name: /Aïcha Tresses/ })).toHaveCount(0);
  });
}

test("search by words, as dictated", async ({ page }) => {
  await page.goto("/fr/explore?q=" + encodeURIComponent("tresses à Calavi"));
  const results = page.getByRole("region", { name: /pros trouvées/ });
  await expect(results.getByRole("link", { name: /Fifonsi Tresses/ })).toBeVisible();
  await expect(results.getByRole("link", { name: /Sènami Hair/ })).toBeVisible();
  // Braids in Cotonou, not in Calavi: every word must match.
  await expect(results.getByRole("link", { name: /Aïcha Tresses/ })).toHaveCount(0);
});

test("explore map groups the pros", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/explore?view=map&city=Cotonou", {
    theme: "light",
    textSize: "normal",
  });
  const map = page.getByRole("region", { name: "Carte des pros" });
  await expect(map.locator("canvas")).toBeVisible({ timeout: 60_000 });
  await expectNoSeriousA11yIssue(page);
  await map.scrollIntoViewIfNeeded();
  await page.waitForTimeout(5000);
  await page.screenshot({ path: "e2e/screenshots/explore-map-mobile.png" });
});
