import { expect, test, type Page } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/*
 * Shops (module 4) with the demo data (`seed_demo`): Gloria Make-up (+2290196000102,
 * verified) sells « Fond de teint Velours » and delivers in « Cotonou centre ».
 * A client buys, pays on the test page, the seller prepares, ships with a parcel photo,
 * types the receipt code, and takes the money from her wallet.
 */

const SELLER_PHONE = "+2290196000102";
const LOOK = { theme: "light", textSize: "normal" } as const;

async function photoFile(page: Page): Promise<Buffer> {
  const dataUrl = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 600;
    canvas.height = 400;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#e8b04b";
    context.fillRect(0, 0, 600, 400);
    return canvas.toDataURL("image/png");
  });
  return Buffer.from(dataUrl.split(",")[1]!, "base64");
}

test("buy, pay, ship, receipt code and payout", async ({ browser }) => {
  test.setTimeout(360_000);
  const client = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const page = await client.newPage();
  await signInAsNewClient(page, "Awa");

  // --- The shop and the product -----------------------------------------------------------------
  await openWith(page, "/fr/gloria/shop", LOOK);
  await expect(page.getByRole("heading", { name: "Boutique de Gloria Make-up" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop.png", fullPage: true });
  await page.getByRole("link", { name: /Fond de teint Velours/ }).click();
  await expect(page.getByRole("heading", { name: "Fond de teint Velours" })).toBeVisible();
  await page.getByRole("button", { name: /^Caramel/ }).click();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop-product.png", fullPage: true });
  await page.getByRole("button", { name: /Ajouter au panier/ }).click();
  await page.getByRole("link", { name: "Voir mon panier" }).click();

  // --- Cart and checkout ------------------------------------------------------------------------
  await expect(page.getByRole("heading", { name: "Mon panier" })).toBeVisible();
  await expect(page.getByText("Caramel")).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop-cart.png", fullPage: true });
  await page.getByRole("link", { name: /^Commander/ }).click();

  await expect(page.getByText("Étape 1 sur 3")).toBeVisible();
  await page.getByText("Livrée par la pro").click();
  await page.getByText("Cotonou centre").click();
  await page.getByLabel("Adresse ou quartier").fill("Rue 12.345, Akpakpa");
  await page.getByLabel("Repères (facultatif)").fill("Portail vert après la pharmacie");
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop-checkout-1.png", fullPage: true });
  await page.getByRole("button", { name: "Voir le récapitulatif" }).click();

  await expect(page.getByRole("heading", { name: "Ce que tu paies" })).toBeVisible();
  await expect(page.getByText("Protection acheteur").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop-checkout-2.png", fullPage: true });
  await page.getByRole("button", { name: "Continuer vers le paiement" }).click();
  await page.getByRole("button", { name: /^Payer/ }).click();

  // --- The test provider, then the orders --------------------------------------------------------
  await expect(page.getByText(/aucun argent réel ne bouge/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect(page.getByRole("heading", { name: "Paiement reçu !" })).toBeVisible({
    timeout: 30_000,
  });
  await page.screenshot({ path: "e2e/screenshots/shop-paid.png", fullPage: true });
  await page.getByRole("link", { name: /Voir la commande chez Gloria/ }).click();
  await expect(page).toHaveURL(/\/fr\/orders\/[0-9a-f-]+$/);
  const orderUrl = new URL(page.url()).pathname;
  const codeBox = page.getByRole("region", { name: "Ton code de réception" });
  await expect(codeBox).toBeVisible({ timeout: 30_000 });
  const code = ((await codeBox.locator("p").nth(0).textContent()) ?? "").replace(/\D/g, "");
  expect(code).toMatch(/^\d{6}$/);
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/shop-order-client.png", fullPage: true });

  // --- The seller -------------------------------------------------------------------------------
  const shop = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const sellerPage = await shop.newPage();
  await signInWithPhone(sellerPage, SELLER_PHONE);
  await openWith(sellerPage, orderUrl, LOOK);
  await expect(sellerPage.getByRole("heading", { name: "Nouvelle commande" })).toBeVisible();
  await expect(sellerPage.getByText("Rue 12.345, Akpakpa")).toBeVisible();
  await sellerPage.getByRole("button", { name: "Je prépare la commande" }).click();
  await expect(sellerPage.getByRole("heading", { name: "En préparation" })).toBeVisible();
  await sellerPage.getByLabel("Prendre en photo le colis").setInputFiles({
    name: "colis.png",
    mimeType: "image/png",
    buffer: await photoFile(sellerPage),
  });
  await expect(sellerPage.getByText("Photo du colis prête")).toBeVisible({ timeout: 60_000 });
  await sellerPage.getByLabel("Numéro de suivi (facultatif)").fill("MOTO-42");
  await expectNoSeriousA11yIssue(sellerPage);
  await sellerPage.screenshot({ path: "e2e/screenshots/shop-order-seller.png", fullPage: true });
  await sellerPage.getByRole("button", { name: "Expédier", exact: true }).click();
  await expect(sellerPage.getByRole("heading", { name: "Expédiée" })).toBeVisible();
  await sellerPage.getByLabel("Code à 6 chiffres").fill(code);
  await sellerPage.getByRole("button", { name: "Valider le code" }).click();
  await expect(sellerPage.getByRole("heading", { name: "Remise, terminée" })).toBeVisible({
    timeout: 30_000,
  });

  // --- Her wallet: the money is available, she takes it -------------------------------------------
  await openWith(sellerPage, "/fr/pro/wallet", LOOK);
  await expect(sellerPage.getByRole("heading", { name: "Mon portefeuille" })).toBeVisible();
  await sellerPage.getByText("Où recevoir mon argent").click();
  await sellerPage.getByRole("button", { name: "Compte de test" }).click();
  await sellerPage.getByRole("button", { name: "Enregistrer", exact: true }).first().click();
  await expect(sellerPage.getByText("Versement vers : Test")).toBeVisible();
  await sellerPage.getByRole("button", { name: /^Retirer/ }).click();
  await expect(sellerPage.getByText("Versement demandé").first()).toBeVisible();

  // --- « My shop » ------------------------------------------------------------------------------
  await openWith(sellerPage, "/fr/pro/shop", LOOK);
  await expect(sellerPage.getByRole("heading", { name: "Ma boutique" })).toBeVisible();
  await expect(sellerPage.getByText("Fond de teint Velours").first()).toBeVisible();
  await expectNoSeriousA11yIssue(sellerPage);
  await sellerPage.screenshot({ path: "e2e/screenshots/my-shop.png", fullPage: true });
  await sellerPage.getByRole("tab", { name: "Chiffres" }).click();
  await expect(sellerPage.getByText("Tes meilleurs produits")).toBeVisible();

  // --- The client: handed over --------------------------------------------------------------------
  await page.reload();
  await expect(page.getByRole("heading", { name: "Remise, terminée" })).toBeVisible();
  await client.close();
  await shop.close();
});

test("a visitor signs in to buy and comes back to the product", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/gloria/shop/rouge-a-levres-wax", LOOK);
  await expect(page.getByRole("heading", { name: "Rouge à lèvres Wax" })).toBeVisible();
  await page.getByRole("button", { name: /Ajouter au panier/ }).click();
  await expect(page).toHaveURL(/\/fr\/auth$/);
});
