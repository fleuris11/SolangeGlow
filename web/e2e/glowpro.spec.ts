import { expect, test, type Page } from "@playwright/test";

import {
  expectNoSeriousA11yIssue,
  openWith,
  signInAsNewClient,
  signInWithPhone,
  VIEWPORTS,
} from "./helpers";

/*
 * Glow Pro (module 8, Premium) with the demo data: Béné Coiffure (+2290196000109).
 * The pro tries Premium, adds a third person, a product with its barcode and what a
 * brushing uses, a package; an appointment is done: the stock and the package go down; she
 * takes cash and gets the receipt and the invoice. A client offers a gift card used at the
 * salon. A campaign leaves for the clients who said yes.
 */

const PRO_PHONE = "+2290196000109";
const LOOK = { theme: "light", textSize: "normal" } as const;
const API = { "X-SG-Client": "web" };

/** A valid EAN-13 (random body, computed check digit): one per run. */
function ean(): string {
  const body = `200${String(Math.floor(Math.random() * 1e9)).padStart(9, "0")}`;
  const sum = [...body]
    .reverse()
    .reduce((total, d, i) => total + Number(d) * (i % 2 === 0 ? 3 : 1), 0);
  return body + String((10 - (sum % 10)) % 10);
}

async function json<T>(response: Awaited<ReturnType<Page["request"]["get"]>>): Promise<T> {
  expect(response.ok(), await response.text()).toBe(true);
  return (await response.json()) as T;
}

test("Premium: team, stock, package, payment at the salon, invoice, gift card, campaign", async ({
  browser,
}) => {
  test.setTimeout(600_000);
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const pro = await context.newPage();
  await signInWithPhone(pro, PRO_PHONE);

  // --- My plan: the free trial ----------------------------------------------------------------
  await openWith(pro, "/fr/pro/plan", LOOK);
  await expect(pro.getByRole("heading", { name: "Mon offre" })).toBeVisible({ timeout: 90_000 });
  const tryIt = pro.getByRole("button", { name: /Essayer gratuitement/ });
  if (await tryIt.isVisible()) {
    await tryIt.click();
    await expect(pro.getByText(/Essai gratuit jusqu'au/)).toBeVisible({ timeout: 30_000 });
  }
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/glowpro-plan.png", fullPage: true });

  // --- A team of three (only with Premium) ----------------------------------------------------
  for (const name of ["Aïcha", "Bintou", "Céline"]) {
    const added = await pro.request.post("/api/v1/me/agenda/staff", {
      data: { name: `${name} ${Date.now() % 1000}` },
      headers: API,
    });
    expect(added.status(), await added.text()).toBe(201);
  }

  // --- Stock: a product with its barcode, found by the scanner, used by a brushing ----------
  const code = ean();
  await openWith(pro, "/fr/pro/stock", LOOK);
  await expect(pro.getByRole("heading", { name: "Stock" })).toBeVisible({ timeout: 90_000 });
  await pro.getByRole("button", { name: "Ajouter un produit" }).click();
  await pro.getByLabel("Nom du produit").fill(`Sérum ${code.slice(-4)}`);
  await pro.getByLabel(/Code-barres/).fill(code);
  await pro.getByLabel("En stock").fill("10");
  await pro.getByLabel("Alerte sous").fill("2");
  await pro.getByRole("button", { name: "Enregistrer" }).click();
  await expect(pro.getByText("Produit ajouté")).toBeVisible();
  await pro.getByRole("button", { name: "Scanner" }).click();
  await pro.getByLabel("Ou tape le code-barres").fill(code);
  await pro.getByRole("button", { name: "Chercher" }).click();
  await expect(pro.getByRole("dialog", { name: `Sérum ${code.slice(-4)}` })).toBeVisible();
  await pro.keyboard.press("Escape");
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/glowpro-stock.png", fullPage: true });

  const items = await json<{ id: string; ean: string; quantity: number }[]>(
    await pro.request.get("/api/v1/me/salon/stock"),
  );
  const serum = items.find((item) => item.ean === code)!;
  const agenda = await json<{ services: { id: string; name: string }[] }>(
    await pro.request.get(`/api/v1/me/agenda?start=${new Date().toISOString().slice(0, 10)}`),
  );
  const brushing = agenda.services.find((s) => s.name === "Brushing")!;
  await json(
    await pro.request.put(`/api/v1/me/salon/services/${brushing.id}/consumption`, {
      data: { rows: [{ item_id: serum.id, quantity: 1 }] },
      headers: API,
    }),
  );

  // --- A package, an appointment of a client who bought it ---------------------------------
  const pack = await json<{ id: string }>(
    await pro.request.post("/api/v1/me/salon/packages", {
      data: { service_id: brushing.id, name: "2 brushings", sessions: 2, price_minor: 5000 },
      headers: API,
    }),
  );
  // Tomorrow (or the day after a Sunday) at 10:00 in Cotonou: within the opening hours.
  const start = new Date(Date.now() + 86_400_000);
  if (start.getUTCDay() === 0) start.setUTCDate(start.getUTCDate() + 1);
  start.setUTCHours(9, 0, 0, 0);
  const nadia = `Nadia ${Date.now() % 10_000}`; // one per run: earlier runs stay in the agenda
  const booked = await json<{
    appointment: { id: string; reference: string };
    record: { id: string };
  }>(
    await pro.request.post("/api/v1/me/agenda/appointments", {
      data: {
        service_id: brushing.id,
        start: start.toISOString(),
        client_name: nadia,
        client_phone: `+2290197${String(Math.floor(Math.random() * 1e6)).padStart(6, "0")}`,
      },
      headers: API,
    }),
  );
  await json(
    await pro.request.post(`/api/v1/me/salon/clients/${booked.record.id}/packages`, {
      data: { package_id: pack.id, method: "cash" },
      headers: API,
    }),
  );
  await json(
    await pro.request.post("/api/v1/dev/booking/time-travel", {
      data: { reference: booked.appointment.reference, starts_in_minutes: -50 },
      headers: API,
    }),
  );

  // --- Done in the agenda, cash taken, receipt and invoice --------------------------------
  await openWith(pro, "/fr/pro/agenda", LOOK);
  await expect(pro.getByRole("heading", { name: "Mon agenda" })).toBeVisible({ timeout: 90_000 });
  // Just after midnight in Cotonou (UTC+1), 50 minutes ago was yesterday.
  const cotonouDay = (ms: number) => new Date(ms + 3_600_000).toISOString().slice(0, 10);
  if (cotonouDay(Date.now() - 50 * 60_000) !== cotonouDay(Date.now())) {
    await pro.getByRole("button", { name: "Précédent" }).click();
  }
  await pro
    .getByRole("button", { name: new RegExp(`^${nadia}, Brushing`) })
    .first()
    .dispatchEvent("click");
  await pro.getByRole("button", { name: "Rendez-vous terminé" }).click();
  await expect(pro.getByText("Terminé. Elle peut laisser un avis.")).toBeVisible();
  await pro.getByRole("radio", { name: "Espèces" }).click();
  const PDF = /\/api\/v1\/documents\/[0-9a-f-]+\.pdf$/;
  const pdfRequest = () => context.waitForEvent("request", (r) => PDF.test(r.url()));
  const receipt = pdfRequest();
  await pro.getByRole("button", { name: "Encaisser" }).last().click();
  await receipt;
  const invoice = pdfRequest();
  await pro.getByRole("button", { name: "Facture PDF" }).click();
  const invoiceUrl = (await invoice).url();
  const pdf = await pro.request.get(invoiceUrl);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  await pro.keyboard.press("Escape");

  const after = await json<{ id: string; quantity: number }[]>(
    await pro.request.get("/api/v1/me/salon/stock"),
  );
  expect(after.find((item) => item.id === serum.id)!.quantity).toBe(9);
  const file = await json<{ packages: { sessions_used: number }[] }>(
    await pro.request.get(`/api/v1/me/salon/clients/${booked.record.id}`),
  );
  expect(file.packages[0]!.sessions_used).toBe(1);

  // --- The dashboard on a phone and on a computer ------------------------------------------
  await openWith(pro, "/fr/pro/dashboard", LOOK);
  await expect(pro.getByText("Agenda rempli")).toBeVisible({ timeout: 90_000 });
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/glowpro-dashboard-mobile.png", fullPage: true });
  await pro.setViewportSize(VIEWPORTS.desktop);
  await pro.screenshot({ path: "e2e/screenshots/glowpro-dashboard-desktop.png", fullPage: true });
  await pro.setViewportSize(VIEWPORTS.mobile);

  // --- A client offers a gift card, used at the salon ----------------------------------------
  const clientContext = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const client = await clientContext.newPage();
  await signInAsNewClient(client, "Grâce");
  await openWith(client, "/fr/bene-coiffure/offres", LOOK);
  await expect(client.getByRole("heading", { name: "Une carte cadeau" })).toBeVisible({
    timeout: 90_000,
  });
  await client.getByRole("radio").first().click();
  await client.getByLabel("Pour qui").fill("Maman");
  await expectNoSeriousA11yIssue(client);
  await client.getByRole("button", { name: /^Payer [0-9 ]+ FCFA$/ }).click();
  await expect(client.getByText(/aucun argent réel ne bouge/)).toBeVisible({ timeout: 60_000 });
  await client.getByRole("button", { name: /Paiement réussi/ }).click();
  let cardCode = "";
  await expect
    .poll(
      async () => {
        const mine = await json<{ gift_cards: { code: string; status: string }[] }>(
          await client.request.get("/api/v1/salon/mine"),
        );
        cardCode = mine.gift_cards.find((c) => c.status === "active")?.code ?? "";
        return cardCode;
      },
      { timeout: 30_000 },
    )
    .not.toBe("");
  await openWith(pro, "/fr/pro/gift-cards", LOOK);
  await pro.getByLabel("Code de la carte").fill(cardCode);
  await pro.getByRole("button", { name: "Voir le solde" }).click();
  await expect(pro.getByText(/^Solde :/)).toBeVisible();
  await pro.getByLabel("Montant à déduire").fill("2000");
  await pro.getByRole("button", { name: "Déduire de la carte" }).click();
  await expect(pro.getByText(/C'est déduit/)).toBeVisible();

  // --- A campaign for the clients who said yes ------------------------------------------------
  await json(
    await pro.request.patch(`/api/v1/me/salon/clients/${booked.record.id}`, {
      data: { email: "nadia@example.com", email_consent: true },
      headers: API,
    }),
  );
  await openWith(pro, "/fr/pro/campaigns", LOOK);
  await pro.getByRole("button", { name: "Nouvelle campagne" }).click();
  await pro.getByLabel("Nom (pour toi)").fill(`Merci ${Date.now() % 1000}`);
  await pro.getByRole("radio", { name: "Toutes mes clientes" }).check();
  await pro.getByLabel("Objet de l'e-mail").fill("Merci {{ first_name }} !");
  await pro.getByLabel("Message").fill("Merci pour ta visite, {{ first_name }}.");
  await pro.getByRole("button", { name: "Enregistrer" }).click();
  await expect(pro.getByText("Campagne enregistrée")).toBeVisible();
  await pro
    .getByRole("button", { name: /^Merci/ })
    .first()
    .click();
  await pro.getByRole("button", { name: /^Envoyer à/ }).click();
  await expect(pro.getByText("Campagne envoyée")).toBeVisible();
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/glowpro-campaigns.png", fullPage: true });

  await clientContext.close();
  await context.close();
});
