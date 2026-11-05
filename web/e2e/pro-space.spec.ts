import { expect, test } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

const LOOK = { theme: "light", textSize: "normal" } as const;
const PRO = "+2290196000109"; // Béné Coiffure
const CLIENT = "+2290197000201"; // Awa

for (const [label, viewport] of Object.entries(VIEWPORTS)) {
  test(`the space of a pro is not the space of a client (${label})`, async ({ browser }) => {
    test.setTimeout(240_000);
    const mobile = viewport.width < 1024;
    const context = await browser.newContext({ viewport });
    const pro = await context.newPage();
    await signInWithPhone(pro, PRO);
    await openWith(pro, "/fr/pro", LOOK);
    await expect(pro.getByRole("heading", { name: "Aujourd'hui", level: 1 })).toBeVisible({
      timeout: 90_000,
    });
    const menu = pro.getByRole("navigation", { name: "Menu de mon activité" }).first();
    await expect(menu.getByRole("link", { name: "Agenda", exact: true })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Boutique", exact: true })).toBeVisible();
    await expect(pro.getByRole("link", { name: "Explorer" })).toHaveCount(0);
    await expectNoSeriousA11yIssue(pro);
    if (mobile) await pro.getByRole("button", { name: "Plus" }).click();
    // Leaving is always in sight, even on a short screen.
    const signOut = pro.getByRole("button", { name: "Déconnexion", exact: true });
    await expect(signOut).toBeInViewport();
    await expect(pro.getByRole("link", { name: "Mon espace personnel" })).toBeInViewport();
    await pro.getByRole("link", { name: "Mon espace personnel" }).click();
    await expect(pro).toHaveURL(/\/fr$/);
    await expect(pro.getByRole("heading", { name: "Ton fil" })).toBeVisible({
      timeout: 60_000,
    });
    await expect(
      pro
        .getByRole("link", { name: "Mon activité" })
        .or(pro.getByRole("link", { name: "Mon activité" }))
        .first(),
    ).toBeVisible();
    await context.close();
  });
}

test("she opens a time by hand and a client can book it", async ({ browser }) => {
  test.setTimeout(300_000);
  const proContext = await browser.newContext({ viewport: VIEWPORTS.desktop });
  const pro = await proContext.newPage();
  await signInWithPhone(pro, PRO);
  await openWith(pro, "/fr/pro/creneaux", LOOK);
  await expect(pro.getByRole("heading", { name: "Créneaux et lieux", level: 1 })).toBeVisible({
    timeout: 90_000,
  });
  await expectNoSeriousA11yIssue(pro);
  const day = new Date(Date.now() + 5 * 86_400_000).toISOString().slice(0, 10);
  const opened = pro.getByRole("region", { name: "Ouvrir un créneau" });
  await opened.getByLabel("Jour").fill(day);
  await opened.getByLabel("De").fill("21:00");
  await opened.getByLabel("À").fill("23:00");
  await opened.getByRole("button", { name: "Ouvrir ce créneau" }).click();
  await expect(pro.getByText("Créneau ouvert.")).toBeVisible();

  const visitor = await (await browser.newContext({ viewport: VIEWPORTS.mobile })).newPage();
  await openWith(visitor, "/fr/bene-coiffure/rdv", LOOK);
  await visitor.getByRole("button", { name: /^Brushing/ }).click();
  const staffStep = visitor.getByRole("heading", { name: "Avec qui ?" });
  const timeStep = visitor.getByRole("heading", { name: "Choisis ton créneau" });
  await expect(staffStep.or(timeStep)).toBeVisible();
  if (await staffStep.isVisible()) {
    await visitor.getByRole("button", { name: "Peu importe" }).click();
  }
  await expect(timeStep).toBeVisible();
  const asked = await visitor.request.get("/api/v1/pros/bene-coiffure/booking");
  const service = (await asked.json()).services.find(
    (s: { name: string }) => s.name === "Brushing",
  );
  const slots = await visitor.request.get(
    `/api/v1/pros/bene-coiffure/booking/slots?service=${service.id}&day=${day}&days=1`,
  );
  const starts = (await slots.json()).days[0].slots.map((s: { start: string }) => s.start);
  expect(starts.some((start: string) => start.includes("T20:") || start.includes("T21:"))).toBe(
    true,
  );

  // The pause stops online booking at once; taking it off brings the times back.
  await pro.getByRole("button", { name: "Mettre en pause les réservations" }).click();
  await expect(pro.getByRole("button", { name: "Reprendre les réservations" })).toBeVisible();
  await visitor.goto("/fr/bene-coiffure/rdv", { timeout: 120_000 });
  await expect(visitor.getByText(/ne prend pas de réservation en ligne/)).toBeVisible();
  await pro.getByRole("button", { name: "Reprendre les réservations" }).click();
  await expect(pro.getByRole("button", { name: "Mettre en pause les réservations" })).toBeVisible();
});

test("the page of a professional stands alone, with the way to book always in sight", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/bene-coiffure", LOOK);
  await expect(page.getByRole("heading", { name: "Béné Coiffure", level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: "Choisir un créneau" })).toBeInViewport();
  await expect(page.getByRole("link", { name: "Publier" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Me connecter" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.getByRole("link", { name: "Choisir un créneau" }).click();
  await expect(page).toHaveURL(/\/fr\/bene-coiffure\/rdv$/);
});

test("a client has no professional entry in her menu, and can sign out", async ({ browser }) => {
  test.setTimeout(180_000);
  const context = await browser.newContext({ viewport: VIEWPORTS.desktop });
  const page = await context.newPage();
  await signInWithPhone(page, CLIENT);
  await openWith(page, "/fr", LOOK);
  await expect(page.getByRole("heading", { name: "Ton fil" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByRole("link", { name: "Mon activité" })).toHaveCount(0);
  const signOut = page.getByRole("button", { name: "Déconnexion", exact: true });
  await expect(signOut).toBeVisible();
  await signOut.click();
  await expect(page.getByRole("link", { name: "Me connecter" }).first()).toBeVisible({
    timeout: 60_000,
  });
  await context.close();
});
