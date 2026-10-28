import { expect, test, type Browser, type Page } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/**
 * Calls and lives through the LiveKit server of docker compose, with a fake camera and
 * microphone (Chromium): a video call between a client and Nafi Gélé, a training live of
 * Institut Prisca (question, raised hand, floor), a sales live of Aïcha (bought from the
 * live). Demo data: seed_demo.
 */
const NAFI = "+2290197000104"; // Nafi Gélé, used by no other journey
const AICHA = "+2290197000101"; // her shop has no demo live (Gloria has two)
const PRISCA = "+2290197000108";
const LOOK = { theme: "light", textSize: "normal" } as const;
const API = { "X-SG-Client": "web" };
const MEDIA = {
  permissions: ["camera", "microphone"],
  viewport: VIEWPORTS.mobile,
};

test.use({
  launchOptions: {
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

async function person(browser: Browser): Promise<Page> {
  const context = await browser.newContext(MEDIA);
  const page = await context.newPage();
  return page;
}

async function json<T>(response: Awaited<ReturnType<Page["request"]["get"]>>): Promise<T> {
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as T;
}

const soon = () => new Date(Date.now() + 5 * 60_000).toISOString();
const NOBODY = "00000000-0000-4000-8000-000000000000";

/** The dev server compiles a screen the first time it opens (LiveKit inside): do it now. */
async function warmUp(page: Page, path: string) {
  await page.goto(path, { waitUntil: "load", timeout: 300_000 }).catch(() => undefined);
  await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
}

test("a video call between a client and a pro, without any phone number", async ({ browser }) => {
  test.setTimeout(720_000);
  // Sign-ins first: a code may have to wait, the call must not ring for nobody.
  const pro = await person(browser);
  await signInWithPhone(pro, NAFI);
  const client = await person(browser);
  await signInAsNewClient(client, "Awa");
  await warmUp(client, `/fr/appel/${NOBODY}`);
  await openWith(client, "/fr/nafi-gele", LOOK);
  await client
    .getByRole("button", { name: /Écrire/ })
    .first()
    .click();
  await expect(client).toHaveURL(/\/fr\/messages\/[0-9a-f-]+/, { timeout: 60_000 });
  const conversation = new URL(client.url()).pathname;
  await client.getByLabel("Ton message").fill("Bonjour, je peux vous appeler ?");
  await client.keyboard.press("Enter");

  await client.getByRole("button", { name: "Vidéo" }).click();
  // First opening of the call screen: the dev server compiles it (LiveKit inside).
  await expect(client).toHaveURL(/\/fr\/appel\/[0-9a-f-]+/, { timeout: 180_000 });
  await expect(client.getByText("Ça sonne…").first()).toBeVisible({ timeout: 90_000 });
  await expectNoSeriousA11yIssue(client);
  await client.screenshot({ path: "e2e/screenshots/call-ringing.png", fullPage: true });

  // --- The pro: the call rings in the conversation ------------------------------------------
  await openWith(pro, conversation, LOOK);
  const banner = pro.getByRole("status").filter({ hasText: /t'appelle/ });
  await expect(banner).toBeVisible({ timeout: 30_000 });
  await banner.getByRole("link", { name: "Décrocher" }).click();
  await expect(pro).toHaveURL(/\/fr\/appel\//);

  // Both see the camera of the other one and the call time.
  await expect(client.getByLabel(/Caméra de/)).toBeVisible({ timeout: 60_000 });
  await expect(pro.getByLabel(/Caméra de/)).toBeVisible({ timeout: 60_000 });
  await expect(client.getByLabel("Ma caméra")).toBeVisible();
  await expect(client.getByRole("button", { name: "Raccrocher" })).toBeVisible();
  await expect(pro.locator("body")).not.toContainText("+229");
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/call-video.png", fullPage: true });

  // Audio only, then hang up: a line in the conversation.
  await client.getByRole("button", { name: "Audio seul" }).first().click();
  await expect(client.getByLabel(/Caméra de/)).toBeHidden();
  await client.getByRole("button", { name: "Raccrocher" }).click();
  await expect(client.getByText(/Appel terminé/)).toBeVisible({ timeout: 30_000 });
  await expect(pro.getByText(/Appel terminé/)).toBeVisible({ timeout: 30_000 });
  await client.getByRole("link", { name: "Retour à la conversation" }).click();
  await expect(client.getByText(/Appel vidéo, \d+ min/)).toBeVisible({ timeout: 30_000 });
  await client.screenshot({ path: "e2e/screenshots/call-line.png", fullPage: true });

  await openWith(client, "/fr/appels", LOOK);
  await expect(client.getByRole("heading", { name: "Mes appels" })).toBeVisible();
  await expect(client.getByText(/\d+ min/).first()).toBeVisible();
  await expectNoSeriousA11yIssue(client);
  await client.screenshot({ path: "e2e/screenshots/call-log.png", fullPage: true });
});

test("a training live: questions, raised hand, the floor, the end", async ({ browser }) => {
  test.setTimeout(720_000);
  const trainer = await person(browser);
  await signInWithPhone(trainer, PRISCA);
  const live = await json<{ id: string }>(
    await trainer.request.post("/api/v1/academy/studio/lives", {
      headers: API,
      data: {
        title: "Teint mariée : en direct",
        starts_at: soon(),
        duration_minutes: 30,
        capacity: 20,
      },
    }),
  );
  const student = await person(browser);
  await signInAsNewClient(student, "Bintou");
  await warmUp(student, `/fr/live/training/${NOBODY}`);
  await json(
    await student.request.post(`/api/v1/academy/lives/${live.id}/registration`, { headers: API }),
  );

  // The waiting room of the academy leads to the live room.
  await openWith(student, `/fr/academie/live/${live.id}`, LOOK);
  await student.getByRole("link", { name: /Entrer dans le live|Rejoindre/ }).click();
  await expect(student).toHaveURL(new RegExp(`/fr/live/training/${live.id}`));
  await expect(student.getByText(/Commence dans|Ça commence bientôt/)).toBeVisible({
    timeout: 60_000,
  });

  await openWith(trainer, `/fr/live/training/${live.id}`, LOOK);
  await trainer.getByRole("button", { name: "Passer en direct" }).click();
  await expect(trainer.getByText("En direct").first()).toBeVisible({ timeout: 30_000 });
  await expect(trainer.getByLabel(/Caméra de Institut Prisca/)).toBeVisible({ timeout: 60_000 });

  // The student sees the trainer, writes, raises her hand.
  await expect(student.getByLabel(/Caméra de Institut Prisca/)).toBeVisible({ timeout: 60_000 });
  await student.getByLabel("Écris ta question").fill("Quel fond de teint pour une peau mixte ?");
  await student.getByRole("button", { name: "Envoyer" }).click();
  await student.getByRole("button", { name: "Lever la main" }).click();
  await expect(student.getByRole("button", { name: "Baisser la main" })).toBeVisible();
  await expectNoSeriousA11yIssue(student);
  await student.screenshot({ path: "e2e/screenshots/live-training-student.png", fullPage: true });

  await expect(trainer.getByText("Quel fond de teint pour une peau mixte ?")).toBeVisible({
    timeout: 30_000,
  });
  await expect(trainer.getByText("1 main levée")).toBeVisible({ timeout: 30_000 });
  await trainer.getByRole("button", { name: "Donner la parole" }).click();
  await expect(student.getByText(/Tu as la parole/)).toBeVisible({ timeout: 30_000 });
  await trainer.getByRole("button", { name: "Répondue" }).click();
  await expectNoSeriousA11yIssue(trainer);
  await trainer.screenshot({ path: "e2e/screenshots/live-training-host.png", fullPage: true });

  await trainer.getByRole("button", { name: "Reprendre la parole" }).click();
  await expect(student.getByText(/Tu as la parole/)).toBeHidden({ timeout: 30_000 });
  await trainer.getByRole("button", { name: "Terminer le live" }).click();
  await trainer.getByRole("button", { name: "Oui, terminer" }).click();
  await expect(student.getByText("Le live est fini")).toBeVisible({ timeout: 60_000 });
  await student.screenshot({ path: "e2e/screenshots/live-training-over.png", fullPage: true });
});

test("a sales live: pinned products bought without leaving the live", async ({ browser }) => {
  test.setTimeout(720_000);
  const seller = await person(browser);
  await signInWithPhone(seller, AICHA);
  const client = await person(browser);
  await signInAsNewClient(client, "Fifamè");
  await warmUp(seller, `/fr/live/sale/${NOBODY}`);
  await warmUp(client, "/fr/checkout");
  const planned = await json<{ results: { id: string; title: string }[] }>(
    await seller.request.post("/api/v1/me/shop/lives", {
      headers: API,
      data: { title: "Gloss en direct", starts_at: soon(), duration_minutes: 30 },
    }),
  );
  const saleId = planned.results.find((row) => row.title === "Gloss en direct")!.id;

  await openWith(seller, `/fr/live/sale/${saleId}`, LOOK);
  await seller.getByRole("button", { name: "Passer en direct" }).click();
  await expect(seller.getByLabel(/Caméra de Aïcha/)).toBeVisible({ timeout: 60_000 });
  await seller.getByRole("button", { name: "Montrer mes produits" }).click();
  await seller.getByRole("dialog").getByRole("button", { name: "Épingler" }).first().click();
  await expect(seller.getByRole("dialog").getByRole("button", { name: "Retirer" })).toBeVisible();
  await seller.keyboard.press("Escape");

  // A visitor without account watches; the shop page shows the live.
  const visitor = await person(browser);
  await openWith(visitor, "/fr/aicha/shop", LOOK);
  await visitor.getByRole("link", { name: /Gloss en direct/ }).click();
  await expect(visitor.getByLabel(/Caméra de Aïcha/)).toBeVisible({ timeout: 60_000 });
  await expect(visitor.getByRole("heading", { name: "Produits du moment" })).toBeVisible({
    timeout: 30_000,
  });
  await expectNoSeriousA11yIssue(visitor);
  await visitor.screenshot({ path: "e2e/screenshots/live-sale-viewer.png", fullPage: true });

  // A client buys from the live: the payment opens in a new tab, the live goes on.
  await openWith(client, `/fr/live/sale/${saleId}`, LOOK);
  await client.getByRole("button", { name: "Acheter" }).first().click();
  const sheet = client.getByRole("dialog");
  await sheet.getByRole("button", { name: /Ajouter au panier/ }).click();
  await expect(sheet.getByText("C'est dans ton panier")).toBeVisible();
  const [checkout] = await Promise.all([
    client.context().waitForEvent("page"),
    sheet.getByRole("link", { name: /Payer mon panier/ }).click(),
  ]);
  await expect(checkout.getByText("Étape 1 sur 3")).toBeVisible({ timeout: 180_000 });
  const pickup = checkout.getByText(/Retrait/).first();
  if (await pickup.count()) await pickup.click();
  await checkout.getByRole("button", { name: "Voir le récapitulatif" }).click();
  await checkout.getByRole("button", { name: "Continuer vers le paiement" }).click();
  await checkout.getByRole("button", { name: /^Payer/ }).click();
  await checkout.getByRole("button", { name: /Paiement réussi/ }).click();
  await expect(checkout.getByRole("heading", { name: "Paiement reçu !" })).toBeVisible({
    timeout: 30_000,
  });

  // Everybody in the room sees the purchase.
  await expect(seller.getByText("1 achat").first()).toBeVisible({ timeout: 30_000 });
  await expect(client.getByLabel(/Caméra de Aïcha/)).toBeVisible();
  await expectNoSeriousA11yIssue(seller);
  await seller.screenshot({ path: "e2e/screenshots/live-sale-host.png", fullPage: true });

  await seller.getByRole("button", { name: "Terminer le live" }).click();
  await seller.getByRole("button", { name: "Oui, terminer" }).click();
  await expect(visitor.getByText("Le live est fini")).toBeVisible({ timeout: 60_000 });
});

test("the home page shows the coming lives", async ({ browser }) => {
  const page = await person(browser);
  await openWith(page, "/fr", LOOK);
  await expect(page.getByRole("heading", { name: "Lives à venir" })).toBeVisible({
    timeout: 90_000,
  });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/live-home.png", fullPage: true });
  await openWith(page, "/fr/gloria/shop", LOOK);
  await expect(page.getByRole("heading", { name: "Lives de la boutique" })).toBeVisible();
});
