import { expect, test, type Page } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/*
 * Secure payment (module 5) with the test provider: a client pays, the money is held, the
 * seller ships and types the receipt code, the money reaches her wallet, she takes it.
 * Uses the demo data (`seed_demo`): Gloria Make-up (+2290196000102, verified).
 */

const SELLER_PHONE = "+2290196000102";
const SELLER_SLUG = "gloria";
const HEADERS = { "X-SG-Client": "web" };

async function demoOrder(page: Page, items = 10_000): Promise<string> {
  const created = await page.request.post("/api/v1/dev/payments", {
    data: {
      seller_slug: SELLER_SLUG,
      items_minor: items,
      delivery_minor: 1_000,
      description: "Maquillage de soirée (démo)",
    },
    headers: HEADERS,
  });
  expect(created.ok(), await created.text()).toBe(true);
  return (await created.json()).id as string;
}

async function payWithTheTestPage(page: Page, id: string, name: string) {
  await openWith(page, `/fr/pay/test/${id}`, { theme: "light", textSize: "normal" });
  await expect(page.getByText(/aucun argent réel ne bouge/)).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: `e2e/screenshots/${name}-test-page.png`, fullPage: true });
  await page.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect(page).toHaveURL(new RegExp(`/fr/payments/${id}$`));
  // The test provider confirms through a webhook (worker): the page looks again by itself.
  await expect(page.getByRole("region", { name: "Ton code de réception" })).toBeVisible({
    timeout: 30_000,
  });
}

test("pay, ship, receipt code, wallet and payout", async ({ browser }) => {
  test.setTimeout(300_000);
  const client = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const page = await client.newPage();
  await signInAsNewClient(page, "Awa");
  const id = await demoOrder(page);
  await payWithTheTestPage(page, id, "payment");

  const code =
    (await page
      .getByRole("region", { name: "Ton code de réception" })
      .locator("p")
      .nth(0)
      .textContent()) ?? "";
  const digits = code.replace(/\D/g, "");
  expect(digits).toMatch(/^\d{6}$/);
  await expect(page.getByText("Payé, argent bloqué").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/payment-client-held.png", fullPage: true });

  // --- The seller -----------------------------------------------------------------------------
  const shop = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const sellerPage = await shop.newPage();
  await signInWithPhone(sellerPage, SELLER_PHONE);
  await openWith(sellerPage, `/fr/payments/${id}`, { theme: "light", textSize: "normal" });
  await expect(sellerPage.getByText("Pour toi")).toBeVisible();
  await expect(sellerPage.getByText(/Paiement reçu et bloqué/)).toBeVisible();
  await expectNoSeriousA11yIssue(sellerPage);
  await sellerPage.screenshot({ path: "e2e/screenshots/payment-seller-held.png", fullPage: true });

  await sellerPage.getByLabel("Transporteur (facultatif)").fill("Gozem");
  await sellerPage.getByRole("button", { name: /C'est parti/ }).click();
  await expect(sellerPage.getByText("Expédié").first()).toBeVisible();
  await sellerPage.getByLabel("Code à 6 chiffres").fill("000000");
  await sellerPage.getByRole("button", { name: "Valider le code" }).click();
  await expect(sellerPage.getByText(/Essais restants : 4/)).toBeVisible();
  await sellerPage.getByLabel("Code à 6 chiffres").fill(digits);
  await sellerPage.getByRole("button", { name: "Valider le code" }).click();
  await expect(sellerPage.getByText("Terminé, argent versé").first()).toBeVisible();
  await sellerPage.screenshot({
    path: "e2e/screenshots/payment-seller-released.png",
    fullPage: true,
  });

  // --- Her wallet --------------------------------------------------------------------------------
  await openWith(sellerPage, "/fr/pro/wallet", { theme: "light", textSize: "normal" });
  await expect(sellerPage.getByRole("heading", { name: "Mon portefeuille" })).toBeVisible();
  await sellerPage.getByText("Où recevoir mon argent").click();
  await sellerPage.getByRole("button", { name: "Compte de test" }).click();
  await sellerPage.getByRole("button", { name: "Enregistrer", exact: true }).first().click();
  await expect(sellerPage.getByText("Versement vers : Test")).toBeVisible();
  await expectNoSeriousA11yIssue(sellerPage);
  await sellerPage.screenshot({ path: "e2e/screenshots/wallet.png", fullPage: true });
  await sellerPage.getByRole("button", { name: /^Retirer/ }).click();
  await expect(sellerPage.getByText("Versement demandé")).toBeVisible();

  // --- The client: completed ----------------------------------------------------------------------
  await page.reload();
  await expect(page.getByText("Terminé, argent versé").first()).toBeVisible();
  await expect(page.getByRole("region", { name: "Ton code de réception" })).toHaveCount(0);
  await client.close();
  await shop.close();
});

test("a problem opens a dispute room", async ({ page }) => {
  test.setTimeout(240_000);
  await page.setViewportSize(VIEWPORTS.mobile);
  await signInAsNewClient(page, "Inès");
  const id = await demoOrder(page, 15_000);
  await payWithTheTestPage(page, id, "dispute");
  await page.getByRole("button", { name: /Un problème avec ma commande/ }).click();
  await page.getByRole("button", { name: "Pas comme annoncé" }).click();
  await page.getByLabel("Explique en quelques mots").fill("Ce n'est pas la teinte commandée.");
  // Back to the top: the fixed menu bar must not hide a button during the check.
  await page.evaluate(() => window.scrollTo(0, 0));
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/dispute-form.png", fullPage: true });
  await page.getByRole("button", { name: "Ouvrir le litige" }).click();
  await expect(page.getByRole("heading", { name: "Litige en cours" })).toBeVisible();
  await expect(page.getByText("En litige").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/dispute-open.png", fullPage: true });
  await page.getByRole("link", { name: /discussion à trois/ }).click();
  await expect(page.getByRole("heading", { name: /Litige SG-/ })).toBeVisible();
  await page.screenshot({ path: "e2e/screenshots/dispute-room.png" });
});

test("the courier types the code without an account", async ({ browser }) => {
  test.setTimeout(240_000);
  const client = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const page = await client.newPage();
  await signInAsNewClient(page, "Zoé");
  const id = await demoOrder(page, 5_000);
  await payWithTheTestPage(page, id, "courier");
  const code = (
    (await page
      .getByRole("region", { name: "Ton code de réception" })
      .locator("p")
      .nth(0)
      .textContent()) ?? ""
  ).replace(/\D/g, "");

  const shop = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const sellerPage = await shop.newPage();
  await signInWithPhone(sellerPage, SELLER_PHONE);
  const link = await sellerPage.request.post(`/api/v1/payments/${id}/courier-link`, {
    headers: HEADERS,
  });
  const url = new URL((await link.json()).url as string);

  const courier = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const courierPage = await courier.newPage();
  await openWith(courierPage, `/fr${url.pathname}`, { theme: "light", textSize: "normal" });
  await expect(courierPage.getByText(/Commande SG-/)).toBeVisible();
  await expectNoSeriousA11yIssue(courierPage);
  await courierPage.screenshot({ path: "e2e/screenshots/courier.png", fullPage: true });
  await courierPage.getByLabel("Code à 6 chiffres").fill(code);
  await courierPage.getByRole("button", { name: "Valider" }).click();
  await expect(courierPage.getByText("C'est validé !")).toBeVisible();
  await client.close();
  await shop.close();
  await courier.close();
});
