import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

/**
 * Diaspora gifts: Grâce, in Paris, offers a Glow gift card and a service at Aïcha's; the
 * person in Benin opens her secret link without an account (the envelope opens), sees
 * her card code, and books the offered service. Demo data: seed_demo.
 */
const GRACE = "+33612340204"; // demo client in Paris
const LOOK = { theme: "light", textSize: "normal" } as const;

async function tokenOf(page: Page): Promise<string> {
  const share = page.getByRole("link", { name: "Envoyer sur WhatsApp" });
  await expect(share).toBeVisible({ timeout: 30_000 });
  const href = decodeURIComponent((await share.getAttribute("href")) ?? "");
  const token = /\/cadeau\/([\w-]+)/.exec(href)?.[1];
  expect(token, href).toBeTruthy();
  return token!;
}

async function payOnTestPage(page: Page) {
  await expect(page).toHaveURL(/\/pay\/test\//, { timeout: 120_000 });
  await page.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect(page).toHaveURL(/\/fr\/cadeaux\/[0-9a-f-]+\?paid=1/, { timeout: 60_000 });
  await expect(page.getByText("Cadeau payé").first()).toBeVisible({ timeout: 30_000 });
}

/** The dev server compiles a screen the first time it opens: do it before the journey. */
async function warmUp(page: Page, path: string) {
  await page.goto(path, { waitUntil: "load", timeout: 300_000 }).catch(() => undefined);
  await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
}

test.use({ viewport: VIEWPORTS.mobile });

test("a Glow gift card offered from Paris, opened in Cotonou without an account", async ({
  page,
  browser,
}) => {
  test.setTimeout(600_000);
  await signInWithPhone(page, GRACE);
  await warmUp(page, "/fr/cadeau/warm-up");
  await warmUp(page, "/fr/cadeaux");
  await warmUp(page, "/fr/offrir?kind=card");
  await openWith(page, "/fr/offrir?kind=card", LOOK);
  await expect(page.getByRole("heading", { name: "Que veux-tu offrir ?" })).toBeVisible({
    timeout: 120_000,
  });
  await page.getByRole("button", { name: /^30,00/ }).click();
  await expect(page.getByText(/^Valeur 19.678.FCFA/)).toBeVisible({ timeout: 30_000 });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/gift-offer-what.png", fullPage: true });
  await page.getByRole("button", { name: "Continuer" }).click();

  await page.getByLabel("Son prénom").fill("Maman Pélagie");
  await page.getByLabel("Son numéro au Bénin").fill("01 97 00 07 78");
  await page.getByRole("button", { name: "Fête des mères" }).click();
  await page.getByRole("button", { name: "Continuer" }).click();
  await page.getByLabel("Ton message").fill("Bonne fête maman, je pense fort à toi.");
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/gift-offer-message.png", fullPage: true });
  await page.getByRole("button", { name: "Continuer" }).click();

  await expect(page.getByRole("heading", { name: "Paiement" })).toBeVisible();
  await expect(page.getByText(/1 € = 655.957 FCFA/)).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/gift-offer-pay.png", fullPage: true });
  await page.getByRole("button", { name: /Payer 31,80/ }).click();
  await payOnTestPage(page);
  await expect(page.getByText("Envoyé").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/gift-follow-up.png", fullPage: true });
  const token = await tokenOf(page);

  // --- In Cotonou, without an account ------------------------------------------------------------
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const mum = await context.newPage();
  await openWith(mum, `/fr/cadeau/${token}`, LOOK);
  await expect(mum.getByRole("heading", { name: "Maman Pélagie, un cadeau pour toi" })).toBeVisible({
    timeout: 120_000,
  });
  await expectNoSeriousA11yIssue(mum);
  await mum.screenshot({ path: "e2e/screenshots/gift-envelope.png", fullPage: true });
  await mum.getByRole("button", { name: "Ouvrir mon cadeau" }).click();
  await expect(mum.getByRole("img", { name: "Cadeau ouvert" })).toBeVisible();
  await expect(mum.getByText(/Bonne fête maman/)).toBeVisible();
  await expect(mum.getByText(/^[A-Z2-9]{10}$/)).toBeVisible();
  await mum.waitForTimeout(700); // the éclosion ends
  await expectNoSeriousA11yIssue(mum);
  await mum.screenshot({ path: "e2e/screenshots/gift-card-opened.png", fullPage: true });

  // The giver sees it was opened.
  await page.reload();
  await expect(page.getByText("Ouvert").first()).toBeVisible({ timeout: 30_000 });
  await context.close();
});

test("a service offered from Paris, booked in Cotonou by the person herself", async ({
  page,
  browser,
}) => {
  test.setTimeout(600_000);
  await signInWithPhone(page, GRACE);
  await openWith(page, "/fr/aicha", LOOK);
  await page.getByRole("link", { name: "Offrir une prestation" }).click();
  await expect(page).toHaveURL(/\/fr\/offrir\?kind=service&pro=aicha/, { timeout: 120_000 });
  await page.locator("label").filter({ hasText: "FCFA" }).first().click();
  await expect(page.getByText(/^Valeur 15.000.FCFA/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Continuer" }).click();
  await page.getByLabel("Son prénom").fill("Tantie Rose");
  await page.getByLabel("Son numéro au Bénin").fill("+2290197000779");
  await page.getByRole("button", { name: "Anniversaire" }).click();
  await page.getByRole("button", { name: "Continuer" }).click();
  await page.getByRole("button", { name: "Continuer" }).click();
  await page.getByRole("button", { name: /^Payer/ }).click();
  await payOnTestPage(page);
  const token = await tokenOf(page);

  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const aunt = await context.newPage();
  await openWith(aunt, `/fr/cadeau/${token}`, LOOK);
  await aunt.getByRole("button", { name: "Ouvrir mon cadeau" }).click({ timeout: 120_000 });
  await expect(aunt.getByRole("heading", { name: "Choisis ton rendez-vous" })).toBeVisible();
  await aunt.locator("section").getByRole("button", { pressed: false }).filter({ hasText: /^\d/ }).first().click();
  await expectNoSeriousA11yIssue(aunt);
  await aunt.screenshot({ path: "e2e/screenshots/gift-book.png", fullPage: true });
  await aunt.getByRole("button", { name: /^Réserver/ }).click();
  await expect(aunt.getByText("Rendez-vous réservé").first()).toBeVisible({ timeout: 60_000 });
  await expect(aunt.getByRole("link", { name: /Voir mon rendez-vous/ })).toBeVisible();
  await aunt.screenshot({ path: "e2e/screenshots/gift-booked.png", fullPage: true });

  await page.reload();
  await expect(page.getByText("Utilisé").first()).toBeVisible({ timeout: 30_000 });
  await openWith(page, "/fr/cadeaux", LOOK);
  await expect(page.getByRole("heading", { name: "Mes cadeaux" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/gift-mine.png", fullPage: true });
  await context.close();
});
