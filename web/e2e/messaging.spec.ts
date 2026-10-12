import { expect, test } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/*
 * Messaging (module 3): a client writes to a pro from her showcase, the pro answers.
 * Uses the demo data (`seed_demo`): Rachida Nails, +2290161000105.
 * The e2e browser cannot reach the WebSocket (port 8000 of another container): the screens
 * fall back to looking for news every 10 s, which this test also covers.
 */

const PRO_PHONE = "+2290161000105";

test("visitors are invited to sign in", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/messages", { theme: "light", textSize: "normal" });
  await expect(page.getByRole("heading", { name: "Écris aux pros" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Me connecter/ })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/messages-visitor.png", fullPage: true });
});

test("a client writes to a pro, who answers with a quick reply", async ({ browser }) => {
  test.setTimeout(300_000);
  const words = `Bonjour, êtes-vous libre samedi ? (${Date.now() % 10_000})`;

  // --- The client, on her phone ------------------------------------------------------------
  const client = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const page = await client.newPage();
  await signInAsNewClient(page, "Awa");
  await openWith(page, "/fr/rachida-nails", { theme: "light", textSize: "normal" });
  await page.getByRole("button", { name: "Écrire", exact: true }).click();
  await expect(page).toHaveURL(/\/fr\/messages\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Rachida Nails" })).toBeVisible();
  await expect(page.getByText("Dis bonjour à Rachida Nails !")).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/thread-empty.png" });

  await page.getByLabel("Ton message").fill(words);
  await page.getByRole("button", { name: "Envoyer", exact: true }).click();
  await expect(page.getByText(words)).toBeVisible();
  await expect(page.getByText("Envoyé")).toBeVisible();

  // A risky message: the pay-in-the-app warning appears.
  await page.getByLabel("Ton message").fill("Je peux payer par Mobile Money ?");
  await page.getByRole("button", { name: "Envoyer", exact: true }).click();
  await expect(page.getByText("Paie dans l'appli pour être protégée")).toBeVisible({
    timeout: 20_000,
  });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/thread-client.png", fullPage: true });

  await page.getByRole("link", { name: "Retour aux messages" }).click();
  const row = page.getByRole("link", { name: /Rachida Nails/ });
  await expect(row).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/messages-list.png", fullPage: true });
  const conversationUrl = await row.getAttribute("href");

  // --- The pro: saved answers, then she reads and answers --------------------------------
  const pro = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const proPage = await pro.newPage();
  await signInWithPhone(proPage, PRO_PHONE);
  await openWith(proPage, "/fr/pro/messages", { theme: "light", textSize: "normal" });
  await expect(proPage.getByRole("heading", { name: "Réponses rapides" })).toBeVisible();
  await proPage.getByLabel("Nouvelle réponse").fill("Oui c'est disponible !");
  await proPage.getByRole("button", { name: "Ajouter" }).click();
  await proPage.getByRole("button", { name: "Enregistrer mes réponses" }).click();
  await expect(proPage.getByText("Enregistré").first()).toBeVisible();
  // The confirmation floats over the page for a few seconds: check once it is gone.
  await expect(proPage.getByText("Enregistré")).toHaveCount(0, { timeout: 15_000 });
  await expectNoSeriousA11yIssue(proPage);
  await proPage.screenshot({ path: "e2e/screenshots/pro-messages-settings.png", fullPage: true });

  await openWith(proPage, conversationUrl ?? "/fr/messages", {
    theme: "light",
    textSize: "normal",
  });
  await expect(proPage.getByText(words)).toBeVisible();
  await expect(proPage.getByText(/ne paie jamais en dehors de l'appli/).first()).toBeVisible();
  await proPage.getByRole("button", { name: "Oui c'est disponible !" }).first().click();
  await proPage.getByRole("button", { name: "Envoyer", exact: true }).click();
  await expect(proPage.getByText("Envoyé")).toBeVisible();
  await expectNoSeriousA11yIssue(proPage);
  await proPage.screenshot({ path: "e2e/screenshots/thread-pro.png", fullPage: true });

  // --- Back on the client's phone: the answer arrives (without the live socket: polling) ----
  await page.goto(conversationUrl ?? "/fr/messages");
  await expect(page.getByText("Oui c'est disponible !").last()).toBeVisible({ timeout: 30_000 });
  // The pro's phone marked the client's messages read.
  await page.screenshot({ path: "e2e/screenshots/thread-answered.png", fullPage: true });

  await client.close();
  await pro.close();
});

test("dark mode and very large text in a conversation list", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await signInAsNewClient(page);
  await openWith(page, "/fr/messages", { theme: "dark", textSize: "xlarge" });
  await expect(page.getByText("Aucun message pour l'instant")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/messages-empty-dark.png", fullPage: true });
});
