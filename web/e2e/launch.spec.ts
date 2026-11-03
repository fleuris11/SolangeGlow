import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

/*
 * Final journey before opening: one person, one go, on a small phone. She signs up, finds a
 * pro, books, the pro confirms, she buys, pays (test provider), the money is held, the seller
 * hands over with the receipt code, then she reads the rules and takes her data with her.
 * Each module goes deeper in its own file. Uses the demo data (`seed_demo`).
 */

const LOOK = { theme: "light", textSize: "normal" } as const;
const BOOKING_PRO_PHONE = "+2290196000109";
const SELLER_PHONE = "+2290196000102";

async function firstCode(page: Page, international: string): Promise<string> {
  const url = `/api/v1/dev/last-code?destination=${encodeURIComponent(international)}`;
  let code = "";
  await expect
    .poll(
      async () => {
        const response = await page.request.get(url);
        code = response.ok() ? (await response.json()).code : "";
        return code;
      },
      { timeout: 30_000, message: "code sent by the worker (dev endpoint)" },
    )
    .toMatch(/^\d{6}$/);
  return code;
}

test("sign up, find, book, buy, receipt code, rules and my data", async ({ browser }) => {
  test.setTimeout(600_000);
  const national = `0197${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
  const name = `Lina ${national.slice(-3)}`;
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile, acceptDownloads: true });
  const page = await context.newPage();

  // --- Sign up ----------------------------------------------------------------------------------
  await openWith(page, "/fr/auth", LOOK);
  await page.getByLabel("Ton numéro de téléphone").fill(national);
  await page.getByRole("button", { name: "Recevoir mon code" }).click();
  await expect(page.getByRole("heading", { name: "Tape ton code" })).toBeVisible();
  await page.getByLabel("Chiffre 1 sur 6").click();
  await page.keyboard.type(await firstCode(page, `+229${national}`));

  await expect(page).toHaveURL(/\/fr\/welcome/);
  await page.getByRole("button", { name: /Je cherche/ }).click();
  await page.getByRole("button", { name: "Continuer" }).click();
  await expect(page.getByRole("heading", { name: "Ta langue" })).toBeVisible();
  await page.getByRole("button", { name: "Continuer" }).click();
  await page.getByRole("button", { name: "Cotonou", exact: true }).click();
  await page.getByLabel("Jour").selectOption("12");
  await page.getByLabel("Mois").selectOption("4");
  await page.getByLabel("Année").selectOption("1995");
  await expect(page.getByRole("button", { name: "C'est parti" })).toBeDisabled();
  await page.getByRole("checkbox", { name: /J'accepte les conditions/ }).check();
  await page.getByRole("button", { name: "C'est parti" }).click();
  await expect(page.getByRole("heading", { name: "Bienvenue !" })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Découvrir" }).click();
  await expect(page).not.toHaveURL(/welcome/, { timeout: 60_000 });
  const named = await page.request.patch("/api/v1/me", {
    data: { first_name: name },
    headers: { "X-SG-Client": "web" },
  });
  expect(named.ok()).toBe(true);

  // --- Find a pro -------------------------------------------------------------------------------
  await openWith(page, "/fr/explore?q=coiffure", LOOK);
  await expectNoSeriousA11yIssue(page);
  await page
    .getByRole("link", { name: /Béné Coiffure/ })
    .first()
    .click();
  await expect(page).toHaveURL(/\/fr\/bene-coiffure/);
  await expect(page.getByRole("heading", { name: "Béné Coiffure" }).first()).toBeVisible();

  // --- Book -------------------------------------------------------------------------------------
  await openWith(page, "/fr/bene-coiffure/rdv", LOOK);
  await page.getByRole("button", { name: /^Brushing/ }).click();
  const staffStep = page.getByRole("heading", { name: "Avec qui ?" });
  const timeStep = page.getByRole("heading", { name: "Choisis ton créneau" });
  await expect(staffStep.or(timeStep)).toBeVisible();
  if (await staffStep.isVisible()) await page.getByRole("button", { name: "Peu importe" }).click();
  const slot = page.getByRole("button", { name: /^\d{1,2}\sh(\s\d{2})?$/ }).first();
  await expect(slot).toBeVisible({ timeout: 30_000 });
  await slot.click();
  await expect(page.getByRole("heading", { name: "Vérifie et réserve" })).toBeVisible();
  await page.getByRole("button", { name: /^Réserver / }).click();
  await expect(page.getByRole("heading", { name: "Demande envoyée" })).toBeVisible({
    timeout: 30_000,
  });
  await page.screenshot({ path: "e2e/screenshots/launch-booked.png", fullPage: true });

  // --- The pro confirms -------------------------------------------------------------------------
  const proContext = await browser.newContext({ viewport: VIEWPORTS.desktop });
  const pro = await proContext.newPage();
  await signInWithPhone(pro, BOOKING_PRO_PHONE);
  await openWith(pro, "/fr/pro/agenda", LOOK);
  await expect(pro.getByRole("heading", { name: "Mon agenda" })).toBeVisible({ timeout: 90_000 });
  // The first free time may be another day: the list of requests names her.
  const booked = pro.getByRole("button", { name: new RegExp(name) }).first();
  await expect(booked).toBeVisible({ timeout: 30_000 });
  await booked.click();
  await pro.getByRole("button", { name: "Confirmer" }).click();
  await expect(pro.getByText("Confirmé. La cliente est prévenue.")).toBeVisible();
  await proContext.close();

  await openWith(page, "/fr/appointments", LOOK);
  await expect(page.getByText("Béné Coiffure").first()).toBeVisible();
  await expect(page.getByText("Confirmé").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);

  // --- Buy and pay ------------------------------------------------------------------------------
  await openWith(page, "/fr/gloria/shop", LOOK);
  await page.getByRole("link", { name: /Fond de teint Velours/ }).click();
  await page.getByRole("button", { name: /^Caramel/ }).click();
  await page.getByRole("button", { name: /Ajouter au panier/ }).click();
  await page.getByRole("link", { name: "Voir mon panier" }).click();
  await expect(page.getByRole("heading", { name: "Mon panier" })).toBeVisible();
  await page.getByRole("link", { name: /^Commander/ }).click();
  await expect(page.getByText("Étape 1 sur 3")).toBeVisible();
  await page.getByText("Livrée par la pro").click();
  await page.getByText("Cotonou centre").click();
  await page.getByLabel("Adresse ou quartier").fill("Rue 12.345, Akpakpa");
  await page.getByRole("button", { name: "Voir le récapitulatif" }).click();
  await expect(page.getByRole("heading", { name: "Ce que tu paies" })).toBeVisible();
  await page.getByRole("button", { name: "Continuer vers le paiement" }).click();
  await page.getByRole("button", { name: /^Payer/ }).click();
  await expect(page.getByText(/aucun argent réel ne bouge/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect(page.getByRole("heading", { name: "Paiement reçu !" })).toBeVisible({
    timeout: 30_000,
  });
  await page.getByRole("link", { name: /Voir la commande chez Gloria/ }).click();
  await expect(page).toHaveURL(/\/fr\/orders\/[0-9a-f-]+$/);
  const orderUrl = new URL(page.url()).pathname;
  const codeBox = page.getByRole("region", { name: "Ton code de réception" });
  await expect(codeBox).toBeVisible({ timeout: 30_000 });
  const code = ((await codeBox.locator("p").nth(0).textContent()) ?? "").replace(/\D/g, "");
  expect(code).toMatch(/^\d{6}$/);
  await page.screenshot({ path: "e2e/screenshots/launch-paid.png", fullPage: true });

  // --- The seller prepares, ships and types the receipt code ------------------------------------
  const sellerContext = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const seller = await sellerContext.newPage();
  await signInWithPhone(seller, SELLER_PHONE);
  await openWith(seller, orderUrl, LOOK);
  await seller.getByRole("button", { name: "Je prépare la commande" }).click();
  await expect(seller.getByRole("heading", { name: "En préparation" })).toBeVisible();
  await seller.getByLabel("Prendre en photo le colis").setInputFiles({
    name: "colis.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      "base64",
    ),
  });
  await expect(seller.getByText("Photo du colis prête")).toBeVisible({ timeout: 60_000 });
  await seller.getByRole("button", { name: "Expédier", exact: true }).click();
  await expect(seller.getByRole("heading", { name: "Expédiée" })).toBeVisible();
  await seller.getByLabel("Code à 6 chiffres").fill(code);
  await seller.getByRole("button", { name: "Valider le code" }).click();
  await expect(seller.getByRole("heading", { name: "Remise, terminée" })).toBeVisible({
    timeout: 30_000,
  });
  await sellerContext.close();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Remise, terminée" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);

  // --- The rules and her data -------------------------------------------------------------------
  await openWith(page, "/fr/pages/conditions-generales", LOOK);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await openWith(page, "/fr/me", LOOK);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: /Télécharger mes données/ }).click();
  expect((await download).suggestedFilename()).toMatch(/\.zip$/);
  await page.screenshot({ path: "e2e/screenshots/launch-end.png", fullPage: true });
  await context.close();
});
