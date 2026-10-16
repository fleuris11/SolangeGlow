import { expect, test } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/*
 * France Selection (module 6) with the demo data (`seed_demo`): the aisles, a product with
 * its final price per shipping mode, payment on the test page, the parcel tracking, a
 * special request, and the quote waiting for Awa (+2290197000201).
 */

const LOOK = { theme: "light", textSize: "normal" } as const;

test("order a product from France and follow the parcel", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize(VIEWPORTS.mobile);
  await signInAsNewClient(page, "Awa");

  await openWith(page, "/fr/selection", LOOK);
  await expect(page.getByRole("heading", { name: "Sélection France" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/selection.png", fullPage: true });
  await page.getByRole("link", { name: /Tendance/ }).click();
  await expect(page).toHaveURL(/aisle=trending/);
  const productLink = page.getByRole("link", { name: /Fond de teint Fenty/ });
  await expect(productLink).toHaveAttribute("href", "/fr/selection/fond-de-teint-fenty");
  await openWith(page, "/fr/selection/fond-de-teint-fenty", LOOK);

  await expect(page.getByRole("heading", { name: /Fond de teint Fenty/ })).toBeVisible();
  await page.getByRole("button", { name: "385" }).click();
  await page.getByText("Express", { exact: true }).click();
  // Back to the top: the fixed bars must not hide a button during the check.
  await page.evaluate(() => window.scrollTo(0, 0));
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/selection-product.png", fullPage: true });
  await page.getByRole("button", { name: /^Payer/ }).click();

  await expect(page.getByText(/aucun argent réel ne bouge/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: /Paiement réussi/ }).click();
  await page.getByRole("link", { name: "Voir la commande" }).click({ timeout: 30_000 });
  await expect(page).toHaveURL(/\/fr\/selection\/orders\/[0-9a-f-]+$/);
  await expect(page.getByRole("region", { name: "Ton code de réception" })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByRole("heading", { name: "Payée, bientôt commandée" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/selection-tracking.png", fullPage: true });

  // A special request: a link, then « being studied ».
  await openWith(page, "/fr/selection/requests", LOOK);
  await page.getByLabel("Lien du produit").fill("https://www.zara.com/fr/robe-satinee");
  await page.getByLabel(/Précise ce que tu veux/).fill("Taille M, en vert");
  await page.getByRole("button", { name: "Envoyer ma demande" }).click();
  await expect(page.getByText("En cours d'étude")).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/selection-request.png", fullPage: true });
});

test("a quote waits to be paid", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize(VIEWPORTS.mobile);
  await signInWithPhone(page, "+2290197000201");
  await openWith(page, "/fr/selection/requests", LOOK);
  await expect(page.getByText("Robe longue satinée").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /^Payer/ }).first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/selection-quote.png", fullPage: true });
});
