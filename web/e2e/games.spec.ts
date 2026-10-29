import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, signInWithPhone, VIEWPORTS } from "./helpers";

/**
 * The playful side: Awa (demo client, Star level) opens the home page (her daily visit
 * counts), her points, the quiz of the day and the free wheel; then « Help me choose »,
 * the photo challenge, her routine, the calendar, the rankings and her invitation link,
 * opened by a visitor. Demo data: seed_demo. The journeys work again on the same day
 * (quiz already answered, wheel already spun).
 */
const AWA = "+2290197000201";
const LOOK = { theme: "light", textSize: "normal" } as const;
const DARK = { theme: "dark", textSize: "xlarge" } as const;

async function warmUp(page: Page, path: string) {
  await page.goto(path, { waitUntil: "load", timeout: 300_000 }).catch(() => undefined);
  await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
}

test.use({ viewport: VIEWPORTS.mobile });

test("Awa's Glow day: the visit, her points, the quiz and the wheel", async ({ page }) => {
  test.setTimeout(600_000);
  await signInWithPhone(page, AWA);
  for (const path of ["/fr", "/fr/points", "/fr/quiz", "/fr/roue"]) await warmUp(page, path);

  await openWith(page, "/fr", LOOK);
  const band = page.getByRole("region", { name: "Ton jour Glow" });
  await expect(band).toBeVisible({ timeout: 120_000 });
  await expect(band.getByText(/jours? d'affilée/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Gagnante du défi").first()).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-home.png", fullPage: true });

  await openWith(page, "/fr/points", LOOK);
  await expect(page.getByRole("heading", { name: "Mes points", level: 1 })).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByText("Star").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Échanger mes points" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-points.png", fullPage: true });
  await openWith(page, "/fr/points", DARK);
  await expect(page.getByRole("heading", { name: "Mes points", level: 1 })).toBeVisible({
    timeout: 120_000,
  });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-points-dark.png" });

  await openWith(page, "/fr/quiz", LOOK);
  const done = page.getByRole("heading", { name: "Quiz terminé" });
  const step = page.getByText(/Étape \d sur 3/);
  await expect(done.or(step)).toBeVisible({ timeout: 120_000 });
  if (await step.isVisible()) {
    await page.locator("ul button").first().click();
    await expect(page.getByText(/Bonne réponse|Raté/)).toBeVisible({ timeout: 30_000 });
  }
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-quiz.png", fullPage: true });

  await openWith(page, "/fr/roue", LOOK);
  await expect(page.getByRole("heading", { name: "Tes chances" })).toBeVisible({
    timeout: 120_000,
  });
  const spin = page.getByRole("button", { name: /Tourner la roue/ });
  if (await spin.isVisible()) await spin.click();
  await expect(page.getByText(/Tu gagnes|Pas de lot/)).toBeVisible({ timeout: 30_000 });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-wheel.png", fullPage: true });
});

test("help me choose, the photo challenge, the routine, the calendar, rankings and invitation", async ({
  page,
  browser,
}) => {
  test.setTimeout(600_000);
  await signInWithPhone(page, AWA);
  for (const path of ["/fr/choisir", "/fr/defi", "/fr/routine", "/fr/fetes", "/fr/classements"]) {
    await warmUp(page, path);
  }

  await openWith(page, "/fr/choisir", LOOK);
  await expect(page.getByRole("heading", { name: "Aide-moi à choisir", level: 1 })).toBeVisible({
    timeout: 120_000,
  });
  const vote = page.getByRole("button", { name: "Voter pour Tresses" });
  if (await vote.isVisible()) {
    await vote.click();
    await expect(page.getByText("Ton choix")).toBeVisible({ timeout: 30_000 });
  }
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-polls.png", fullPage: true });

  await openWith(page, "/fr/defi", LOOK);
  await expect(page.getByRole("heading", { name: "Look pagne du dimanche" })).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByText("Gagnante du défi")).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-challenge.png", fullPage: true });

  await openWith(page, "/fr/routine", LOOK);
  await expect(page.getByRole("heading", { name: "Ma routine", level: 1 })).toBeVisible({
    timeout: 120_000,
  });
  await page.getByRole("tab", { name: "Matin" }).click();
  const first = page.getByRole("checkbox").first();
  await first.click();
  await expect(first).toHaveAttribute("aria-checked", /true|false/);
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-routine.png", fullPage: true });

  await openWith(page, "/fr/fetes", LOOK);
  await expect(page.getByRole("heading", { name: "Noël" })).toBeVisible({ timeout: 120_000 });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-calendar.png", fullPage: true });

  await openWith(page, "/fr/classements", LOOK);
  await expect(page.getByText(/Classement d/)).toBeVisible({ timeout: 120_000 });
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/games-rankings.png", fullPage: true });

  const me = await (await page.request.get("/api/v1/glow/me")).json();
  const context = await browser.newContext({ viewport: VIEWPORTS.mobile });
  const friend = await context.newPage();
  await warmUp(friend, `/fr/invite/${me.referral.code}`);
  await openWith(friend, `/fr/invite/${me.referral.code}`, LOOK);
  await expect(friend.getByRole("heading", { name: "Awa t'invite sur Solange Glow" })).toBeVisible(
    { timeout: 120_000 },
  );
  await expect(friend.getByRole("link", { name: "Créer mon compte" })).toBeVisible();
  await expectNoSeriousA11yIssue(friend);
  await friend.screenshot({ path: "e2e/screenshots/games-invite.png", fullPage: true });
  await context.close();
});
