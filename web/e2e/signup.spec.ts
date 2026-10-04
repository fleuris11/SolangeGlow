import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { openWith, VIEWPORTS } from "./helpers";

/** A new Benin mobile number for each run (10 digits since 2024). */
function newBeninNumber(): string {
  return `0197${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
}

/** Reads the code the way the person would read it on WhatsApp (dev-only endpoint). */
async function lastCode(page: Page, international: string): Promise<string> {
  const response = await page.request.get(
    `/api/v1/dev/last-code?destination=${encodeURIComponent(international)}`,
  );
  expect(response.ok(), "dev code endpoint (development only)").toBeTruthy();
  return (await response.json()).code;
}

async function expectNoSeriousA11yIssue(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(
    serious,
    JSON.stringify(
      serious.map((v) => [v.id, v.nodes[0]?.target]),
      null,
      2,
    ),
  ).toEqual([]);
}

test.describe("sign-up on a small phone", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
  });

  test("phone number → code → welcome → home, signed in", async ({ page }) => {
    // Needs the Django backend in development mode (codes read from /api/v1/dev/last-code).
    test.skip(!!process.env.CI && !process.env.E2E_WITH_BACKEND, "runs with docker compose");
    const national = newBeninNumber();
    const international = `+229${national}`;

    await openWith(page, "/fr/auth", { theme: "light", textSize: "normal" });
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/auth-1-phone.png", fullPage: true });

    await page.getByLabel("Ton numéro de téléphone").fill(national);
    await page.getByRole("button", { name: "Recevoir mon code" }).click();

    await expect(page.getByRole("heading", { name: "Tape ton code" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Renvoyer dans/ })).toBeDisabled();
    await page.screenshot({ path: "e2e/screenshots/auth-2-code.png", fullPage: true });

    // A wrong code first: clear message, the person stays on the screen.
    await page.getByLabel("Chiffre 1 sur 6").click();
    await page.keyboard.type("000000");
    await expect(
      page.getByRole("alert").filter({ hasText: "Le code ne correspond pas" }),
    ).toBeVisible();
    await page.screenshot({ path: "e2e/screenshots/auth-3-wrong-code.png", fullPage: true });

    // The boxes are emptied and the cursor is back in the first one.
    await expect(page.getByLabel("Chiffre 1 sur 6")).toBeFocused();
    await expect(page.getByLabel("Chiffre 1 sur 6")).toHaveValue("");
    const code = await lastCode(page, international);
    await page.keyboard.type(code);

    // Welcome screens, at most three.
    await expect(page).toHaveURL(/\/fr\/welcome/);
    await expect(page.getByRole("heading", { name: "Tu viens pour quoi ?" })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/welcome-1-role.png", fullPage: true });

    await page.getByRole("button", { name: /Je suis une pro/ }).click();
    await page.getByRole("button", { name: "Tresses" }).click();
    await page.screenshot({ path: "e2e/screenshots/welcome-1-role-pro.png", fullPage: true });
    await page.getByRole("button", { name: "Continuer" }).click();

    await expect(page.getByRole("heading", { name: "Ta langue" })).toBeVisible();
    await page.getByRole("button", { name: "Continuer" }).click();

    await expect(page.getByRole("heading", { name: "Ta ville" })).toBeVisible();
    await page.getByRole("button", { name: "Abomey-Calavi" }).click();
    await page.screenshot({ path: "e2e/screenshots/welcome-3-city.png", fullPage: true });
    await page.getByRole("button", { name: "C'est parti" }).click();

    await expect(page.getByRole("heading", { name: "Bienvenue !" })).toBeVisible();
    await page.screenshot({ path: "e2e/screenshots/welcome-done.png", fullPage: true });
    await page.getByRole("button", { name: "Découvrir" }).click();

    // Home, signed in: "Me" shows the profile and the city chosen.
    await expect(page).toHaveURL(/\/fr$/);
    await page
      .getByRole("navigation", { name: "Menu principal" })
      .last()
      .getByRole("link", { name: "Moi" })
      .click();
    await expect(page.getByText(international)).toBeVisible();
    await expect(page.getByLabel("Ville", { exact: true })).toHaveValue("Abomey-Calavi");
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/me-signed-in.png", fullPage: true });

    // Signing out: "Me" invites to sign in again.
    await page.getByRole("button", { name: "Me déconnecter", exact: true }).click();
    await expect(page).toHaveURL(/\/fr$/);
    await page.goto("/fr/me");
    await expect(page.getByRole("link", { name: "Me connecter ou m'inscrire" })).toBeVisible();
  });

  test("dark mode and very large text on the sign-in page", async ({ page }) => {
    await openWith(page, "/fr/auth", { theme: "dark", textSize: "xlarge" });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/auth-dark-xlarge.png", fullPage: true });
  });
});
