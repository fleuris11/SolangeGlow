import { expect, test } from "@playwright/test";

import { openWith, VIEWPORTS } from "./helpers";

test.describe("app shell on mobile", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile);
    await openWith(page, "/fr", { theme: "light", textSize: "normal" });
  });

  test("changes the city from the bottom sheet and remembers it", async ({ page }) => {
    await page
      .getByRole("button", { name: /Changer de ville/ })
      .first()
      .click();
    const sheet = page.getByRole("dialog", { name: "Choisis ta ville" });
    await expect(sheet).toBeVisible();

    await sheet.getByRole("button", { name: "Paris" }).click();
    await expect(sheet).toBeHidden();
    await expect(page.getByRole("button", { name: /Ville : Paris/ }).first()).toBeVisible();

    await page.reload();
    await expect(page.getByRole("button", { name: /Ville : Paris/ }).first()).toBeVisible();
  });

  test("navigates with the bottom bar", async ({ page }) => {
    const nav = page.getByRole("navigation", { name: "Menu principal" }).last();
    await nav.getByRole("link", { name: "Messages" }).click();
    await expect(page).toHaveURL(/\/fr\/messages$/);
    await expect(page.getByRole("heading", { name: "Aucun message pour l'instant" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Messages" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  test("switches to dark theme and very large text from Me", async ({ page }) => {
    await page.goto("/fr/me");
    await page.getByRole("button", { name: "Sombre" }).click();
    await page.getByRole("button", { name: "Très grand" }).click();

    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(html).toHaveAttribute("data-text-size", "xlarge");
    await expect(page.getByRole("status")).toContainText("Réglage enregistré");
  });
});
