import { expect, test } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, VIEWPORTS } from "./helpers";

const LOOK = { theme: "light", textSize: "normal" } as const;

for (const [label, viewport] of Object.entries(VIEWPORTS)) {
  test(`a visitor sees how to sign up, sign in and start as a pro (${label})`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openWith(page, "/fr", LOOK);
    const main = page.getByRole("main");
    await expect(main.getByRole("link", { name: "Me connecter" }).first()).toBeVisible();
    await expect(main.getByRole("link", { name: "Créer un compte" }).first()).toBeVisible();
    await expect(main.getByRole("link", { name: "Je propose mes services" }).first()).toBeVisible();

    // The ticket answers: the choice changes the photo, the code and the way to the professionals.
    await expect(
      main.getByRole("link", { name: "Trouver un professionnel : tresses" }),
    ).toHaveAttribute("href", "/fr/explore?trade=braids");
    await main.getByText("Maquillage", { exact: true }).first().click();
    await expect(
      main.getByRole("link", { name: "Trouver un professionnel : maquillage" }),
    ).toHaveAttribute("href", "/fr/explore?trade=makeup");
    await expect(main.getByRole("img", { name: /QR code d'exemple/ })).toBeVisible();

    // The two sides of an account.
    await expect(main.getByRole("heading", { name: "Un compte, deux côtés" })).toBeAttached();
    await expect(main.getByRole("link", { name: "Créer mon compte", exact: true })).toHaveAttribute(
      "href",
      "/fr/auth?as=client",
    );
    await main.getByText("Je propose", { exact: true }).click();
    await expect(main.getByRole("link", { name: "Créer ma vitrine" })).toHaveAttribute(
      "href",
      "/fr/auth?as=pro",
    );

    for (const service of [
      "Boutiques",
      "Sélection France",
      "Académie",
      "Lives",
      "Offrir",
      "Messages",
      "Jeux",
      "Écouter",
    ]) {
      await expect(main.getByRole("link", { name: new RegExp(service) }).first()).toBeAttached();
    }
    await expect(main.getByText("Faut-il un compte pour réserver ?")).toBeAttached();
  });
}

test("the name typed on the home page follows to the creation of the page", async ({ page }) => {
  await openWith(page, "/fr", LOOK);
  await page.getByLabel("Le nom de ta vitrine").fill("Aïcha Tresses");
  await page.getByRole("button", { name: "Créer", exact: true }).click();
  await expect(page).toHaveURL(/\/fr\/auth\?as=pro&vitrine=/);
});

test("the page for professionals explains the QR code and what is free, then leads to sign up", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/proposer-mes-services", LOOK);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Ton activité en ligne");
  await expect(page.getByRole("heading", { name: "Ton lien et ton QR code" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Gratuit ou Premium ?" })).toBeVisible();
  await expectNoSeriousA11yIssue(page);
  await page.getByRole("link", { name: "Créer ma vitrine" }).first().click();
  await expect(page).toHaveURL(/\/fr\/auth\?as=pro$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 60_000 });
});

test("how it works lists the accounts and each service", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openWith(page, "/fr/comment-ca-marche", LOOK);
  await expect(page.getByRole("heading", { level: 1, name: "Comment ça marche" })).toBeVisible();
  for (const title of [
    "Les types de compte",
    "Créer un compte",
    "Prendre rendez-vous",
    "Payer en sécurité",
    "Sélection France",
    "Offrir au pays",
    "Te former à l'Académie",
    "Jouer et gagner des points",
  ]) {
    await expect(page.getByRole("heading", { name: title, level: 2 })).toBeVisible();
  }
  await expectNoSeriousA11yIssue(page);
});
