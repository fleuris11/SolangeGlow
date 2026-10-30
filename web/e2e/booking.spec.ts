import { expect, test } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

/*
 * Appointments (module 8) with the demo data (`seed_demo`): Béné Coiffure
 * (+2290196000109) accepts each request by hand; Institut Prisca has a team of four.
 * A guest books without an account, the pro confirms in her agenda, the reminder leaves,
 * the appointment is done, and the guest (now signed in with the same number) reviews it.
 */

const PRO_PHONE = "+2290196000109";
const TEAM_PHONE = "+2290197000108"; // Institut Prisca
const LOOK = { theme: "light", textSize: "normal" } as const;
const API = { "X-SG-Client": "web" };

test("a guest books, the pro confirms, reminder, done, then a verified review", async ({
  browser,
}) => {
  test.setTimeout(480_000);
  const phone = `+2290197${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
  const name = `Inès ${phone.slice(-3)}`; // one per run: earlier runs may have left requests

  // --- The guest books on her phone -------------------------------------------------------------
  const guestContext = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const guest = await guestContext.newPage();
  await openWith(guest, "/fr/bene-coiffure/rdv", LOOK);
  await expect(
    guest.getByRole("heading", { name: "Rendez-vous chez Béné Coiffure" }),
  ).toBeVisible();
  await expectNoSeriousA11yIssue(guest);
  await guest.screenshot({ path: "e2e/screenshots/booking-service.png", fullPage: true });
  await guest.getByRole("button", { name: /^Brushing/ }).click();

  // The team step only shows when several people do the service (Glow Pro runs add some).
  const staffStep = guest.getByRole("heading", { name: "Avec qui ?" });
  const timeStep = guest.getByRole("heading", { name: "Choisis ton créneau" });
  await expect(staffStep.or(timeStep)).toBeVisible();
  if (await staffStep.isVisible()) await guest.getByRole("button", { name: "Peu importe" }).click();
  await expect(timeStep).toBeVisible();
  const slot = guest.getByRole("button", { name: /^\d{1,2}\sh(\s\d{2})?$/ }).first();
  await expect(slot).toBeVisible({ timeout: 30_000 });
  await guest.evaluate(() => window.scrollTo(0, 0));
  await expectNoSeriousA11yIssue(guest);
  await guest.screenshot({ path: "e2e/screenshots/booking-time.png", fullPage: true });
  await slot.click();

  await expect(guest.getByRole("heading", { name: "Vérifie et réserve" })).toBeVisible();
  await guest.getByLabel("Ton prénom").fill(name);
  await guest.getByLabel(/Ton numéro WhatsApp/).fill(phone);
  await guest.getByLabel(/Un mot pour la pro/).fill("Cheveux mi-longs");
  await expectNoSeriousA11yIssue(guest);
  await guest.screenshot({ path: "e2e/screenshots/booking-details.png", fullPage: true });
  await guest.getByRole("button", { name: /^Réserver / }).click();

  await expect(guest.getByRole("heading", { name: "Demande envoyée" })).toBeVisible({
    timeout: 30_000,
  });
  const reference = (await guest.getByText(/^Référence RDV-/).textContent())!.replace(
    "Référence ",
    "",
  );
  await expectNoSeriousA11yIssue(guest);
  const manageUrl = (await guest
    .getByRole("link", { name: "Voir mon rendez-vous" })
    .getAttribute("href"))!;
  expect(manageUrl).toMatch(/^\/fr\/rdv\//);
  // First visit of a page: the development server compiles it.
  await guest.goto(manageUrl, { timeout: 120_000 });
  await expect(guest.getByRole("heading", { name: "À confirmer par la pro" })).toBeVisible({
    timeout: 60_000,
  });

  // --- The pro confirms in her agenda (computer) -----------------------------------------------
  const proContext = await browser.newContext({ viewport: VIEWPORTS.desktop });
  const pro = await proContext.newPage();
  await signInWithPhone(pro, PRO_PHONE);
  await openWith(pro, "/fr/pro/agenda", LOOK);
  await expect(pro.getByRole("heading", { name: "Mon agenda" })).toBeVisible({ timeout: 90_000 });
  await pro
    .getByRole("button", { name: new RegExp(name) })
    .first()
    .click();
  await expect(pro.getByText("« Cheveux mi-longs »")).toBeVisible();
  await pro.getByRole("button", { name: "Confirmer" }).click();
  await expect(pro.getByText("Confirmé. La cliente est prévenue.")).toBeVisible();
  await pro.keyboard.press("Escape");

  await guest.goto(manageUrl);
  await expect(guest.getByRole("heading", { name: "Confirmé" })).toBeVisible();
  await expectNoSeriousA11yIssue(guest);
  await guest.screenshot({ path: "e2e/screenshots/booking-guest-link.png", fullPage: true });

  // --- The reminder (the appointment now starts in 90 minutes) ---------------------------------
  const soon = await pro.request.post("/api/v1/dev/booking/time-travel", {
    data: { reference, starts_in_minutes: 90 },
    headers: API,
  });
  expect(soon.ok(), await soon.text()).toBe(true);
  expect((await soon.json()).reminders).toBeGreaterThanOrEqual(1);

  // --- Done (it started 30 minutes ago) --------------------------------------------------------
  const started = await pro.request.post("/api/v1/dev/booking/time-travel", {
    data: { reference, starts_in_minutes: -30 },
    headers: API,
  });
  expect(started.ok()).toBe(true);
  await openWith(pro, "/fr/pro/agenda", LOOK);
  // Just after midnight in Cotonou (UTC+1, no summer time), « 30 minutes ago » is still
  // yesterday, while the agenda opens on today.
  const cotonou = new Date(Date.now() + 60 * 60_000);
  if (cotonou.getUTCHours() * 60 + cotonou.getUTCMinutes() < 30) {
    await pro.getByRole("button", { name: "Précédent", exact: true }).click();
  }
  const block = pro.getByRole("button", { name: new RegExp(`^${name}, Brushing`) }).first();
  await expect(block).toBeVisible({ timeout: 30_000 });
  await expectNoSeriousA11yIssue(pro);
  await pro.screenshot({ path: "e2e/screenshots/agenda-desktop.png", fullPage: true });
  await block.click();
  await pro.getByRole("button", { name: "Rendez-vous terminé" }).click();
  await expect(pro.getByText("Terminé. Elle peut laisser un avis.")).toBeVisible();

  // --- The guest signs in with the same number and leaves a verified review --------------------
  await signInWithPhone(guest, phone);
  const onboarded = await guest.request.post("/api/v1/me/onboarding", {
    data: { mode: "client", birth_date: "1995-04-12", city: "Cotonou" },
    headers: API,
  });
  expect(onboarded.ok()).toBe(true);
  await openWith(guest, "/fr/appointments", LOOK);
  await expect(guest.getByRole("heading", { name: "Mes rendez-vous" })).toBeVisible();
  await expect(guest.getByText("Brushing").first()).toBeVisible();
  await openWith(guest, "/fr/me/reviews", LOOK);
  await expect(guest.getByRole("button", { name: "5 étoiles" }).first()).toBeVisible({
    timeout: 60_000,
  });
  await guest.getByRole("button", { name: "5 étoiles" }).first().click();
  await guest.getByRole("button", { name: "Envoyer mon avis" }).first().click();
  await expect(guest.getByText("Merci pour ton avis !")).toBeVisible();

  await guestContext.close();
  await proContext.close();
});

test("the agenda of a team, on a phone and on a computer", async ({ browser }) => {
  test.setTimeout(240_000);
  for (const viewport of [VIEWPORTS.mobile, VIEWPORTS.desktop]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await signInWithPhone(page, TEAM_PHONE);
    const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    await openWith(page, `/fr/pro/agenda?day=${tomorrow}`, LOOK);
    await expect(page.getByRole("heading", { name: "Mon agenda" })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText("Mireille").first()).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    const name = viewport.width < 400 ? "agenda-mobile" : "agenda-team-desktop";
    await page.screenshot({ path: `e2e/screenshots/${name}.png`, fullPage: true });
    if (viewport.width < 400) {
      await openWith(page, "/fr/pro/agenda/settings", LOOK);
      await expect(page.getByRole("heading", { name: "Réglages de l'agenda" })).toBeVisible();
      await expectNoSeriousA11yIssue(page);
      await page.screenshot({ path: "e2e/screenshots/agenda-settings.png", fullPage: true });
    }
    await context.close();
  }
});
