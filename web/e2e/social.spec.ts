import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, VIEWPORTS, type Theme } from "./helpers";

/*
 * Social network (module 2) and moderation (module 12): feed, stories, post page,
 * likes, comments, « Publier », followed profiles, reports.
 * Uses the demo data: `docker compose exec backend python manage.py seed_demo`.
 */

const SIZES = ["mobile", "desktop"] as const;
const THEMES: Theme[] = ["light", "dark"];

/** A new client, signed in through the API (same cookies as the browser). */
async function signInAsNewClient(page: Page) {
  const phone = `+2290197${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
  const headers = { "X-SG-Client": "web" };
  const asked = await page.request.post("/api/v1/auth/otp/request", { data: { phone }, headers });
  expect(asked.ok()).toBe(true);
  const { challenge_id } = await asked.json();
  let code = "";
  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          `/api/v1/dev/last-code?destination=${encodeURIComponent(phone)}`,
        );
        code = response.ok() ? (await response.json()).code : "";
        return code;
      },
      { timeout: 30_000, message: "code sent by the worker (dev endpoint)" },
    )
    .toMatch(/^\d{6}$/);
  const verified = await page.request.post("/api/v1/auth/otp/verify", {
    data: { challenge_id, code },
    headers,
  });
  expect(verified.ok()).toBe(true);
  const onboarded = await page.request.post("/api/v1/me/onboarding", {
    data: { mode: "client", birth_date: "1995-04-12", city: "Cotonou" },
    headers,
  });
  expect(onboarded.ok()).toBe(true);
}

function noHorizontalScroll(page: Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
}

for (const size of SIZES) {
  for (const theme of THEMES) {
    test(`home feed and stories ${size} ${theme}`, async ({ page }) => {
      await page.setViewportSize(VIEWPORTS[size]);
      await openWith(page, "/fr", { theme, textSize: "normal" });
      await expect(page.getByRole("heading", { name: "Les looks du moment" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Aujourd'hui", exact: true })).toBeVisible();
      await expect(page.getByRole("article").first()).toBeVisible();
      await expectNoSeriousA11yIssue(page);
      expect(await noHorizontalScroll(page)).toBeLessThanOrEqual(0);
      await page.screenshot({ path: `e2e/screenshots/home-feed-${size}-${theme}.png` });
    });
  }
}

test("the feed is on the page before any script runs", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/fr");
  await expect(page.getByRole("article").first()).toBeVisible();
  await context.close();
});

test("stories open one by one, free slots first", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr", { theme: "light", textSize: "normal" });
  const strip = page.getByRole("region", { name: "Aujourd'hui" });
  await strip.getByRole("button").filter({ hasText: "Libre" }).first().click();
  const sheet = page.getByRole("dialog");
  await expect(sheet.getByText("Créneaux libres aujourd'hui")).toBeVisible();
  await expect(sheet.getByRole("link", { name: /Voir sa vitrine pour réserver/ })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/story-free-slots.png" });
  await sheet.getByRole("button", { name: /Suivante|Terminer/ }).click();
});

test("post page with comments and a sharing preview", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr", { theme: "light", textSize: "normal" });
  await page
    .getByRole("article")
    .first()
    .getByRole("link", { name: /commentaire|Commenter/ })
    .click();
  await expect(page).toHaveURL(/\/fr\/p\/[0-9a-f-]+#comments$/);
  await expect(page.getByRole("heading", { name: "Commentaires" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Connecte-toi pour commenter" })).toBeVisible();
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
    "content",
    /Publication de/,
  );
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\.webp/);
  await expectNoSeriousA11yIssue(page);
  await page.screenshot({ path: "e2e/screenshots/post-page.png", fullPage: true });
});

test.describe("signed in", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await signInAsNewClient(page);
  });

  test("like, save, share, comment, report and follow", async ({ page }) => {
    test.setTimeout(240_000);
    await openWith(page, "/fr", { theme: "light", textSize: "normal" });
    await expect(page.getByRole("heading", { name: "Ton fil" })).toBeVisible();
    const post = page.getByRole("article").first();

    const like = post.getByRole("button", { name: /^J'aime/ });
    await like.click();
    await expect(post.getByRole("button", { name: /^Je n'aime plus/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await post.getByRole("button", { name: "Enregistrer" }).click();
    await expect(page.getByText("Enregistré", { exact: true })).toBeVisible();

    // Share sheet.
    await post.getByRole("button", { name: "Partager" }).click();
    const share = page.getByRole("dialog", { name: "Partager" });
    await expect(share.getByRole("button", { name: /WhatsApp/ })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/post-share.png" });
    await page.keyboard.press("Escape");

    // Comment, then see it on the post page.
    await post.getByRole("link", { name: /commentaire|Commenter/ }).click();
    await expect(page.getByRole("heading", { name: "Commentaires" })).toBeVisible();
    const words = `Magnifique travail ${Date.now() % 10_000}`;
    await page.getByLabel("Ton commentaire").fill(words);
    await page.getByRole("button", { name: "Envoyer" }).click();
    await expect(page.getByText(words)).toBeVisible();
    const postUrl = page.url();
    // Back to the top: the fixed menu bar must not hide a button during the check.
    await page.evaluate(() => window.scrollTo(0, 0));
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/post-commented.png", fullPage: true });

    // Saved posts.
    await page.goto("/fr/saved");
    await expect(page.getByRole("heading", { name: "Enregistrés" })).toBeVisible();
    await expect(page.getByRole("article")).toHaveCount(1);

    // Report the post with a reason (last: enough reports hide it automatically).
    await page.goto(postUrl, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Plus d'options" }).click();
    await page
      .getByRole("dialog", { name: "Options" })
      .getByRole("button", { name: /Signaler/ })
      .click();
    await page.screenshot({ path: "e2e/screenshots/post-report.png" });
    await page.getByRole("button", { name: "Spam ou publicité" }).click();
    await expect(page.getByText("Merci. Notre équipe va regarder.")).toBeVisible();

    // Follow a pro from her showcase, then find her in « Profils suivis ».
    await page.goto("/fr/aicha");
    await page.getByRole("button", { name: "Suivre", exact: true }).click();
    await expect(page.getByRole("button", { name: "Suivie" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await page.goto("/fr/following");
    await expect(page.getByRole("heading", { name: "Profils suivis" })).toBeVisible();
    await expect(page.getByText("Aïcha Tresses")).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/following.png", fullPage: true });
  });

  test("« Publier »: a text story in three steps", async ({ page }) => {
    await openWith(page, "/fr/create", { theme: "light", textSize: "normal" });
    await expect(page.getByRole("heading", { name: "Que veux-tu publier ?" })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/create-1.png", fullPage: true });
    await page.getByRole("button", { name: "Texte sur fond" }).click();
    await page.getByRole("button", { name: "Continuer" }).click();
    await page.getByLabel("Ton message").fill("Dispo ce soir à Cotonou");
    await page.getByRole("button", { name: "Prune" }).click();
    await page.screenshot({ path: "e2e/screenshots/create-2.png", fullPage: true });
    await page.getByRole("button", { name: "Continuer" }).click();
    await expect(page.getByText("Aperçu", { exact: true })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/create-3.png", fullPage: true });
    await page.getByRole("button", { name: "Publier la story" }).click();
    await expect(page).toHaveURL(/\/fr$/);
    // Her story is in today's strip (she has not given her first name yet).
    await expect(
      page.getByRole("region", { name: "Aujourd'hui" }).getByText("Membre Solange Glow").first(),
    ).toBeVisible();
  });

  test("empty states are helpful", async ({ page }) => {
    await openWith(page, "/fr/following", { theme: "light", textSize: "normal" });
    await expect(page.getByText("Tu ne suis personne pour l'instant")).toBeVisible();
    await expect(page.getByRole("link", { name: "Découvrir des pros" })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/following-empty.png", fullPage: true });
    await page.goto("/fr/me/reviews");
    await expect(page.getByText("Aucun avis à laisser")).toBeVisible();
    await expectNoSeriousA11yIssue(page);
  });
});
