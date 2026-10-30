import { createHmac } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yIssue, openWith, VIEWPORTS } from "./helpers";

/**
 * Back office (module 12): the owner signs in with her two-factor code, then the dashboard,
 * the consoles, the team, the switches, the translations and the journal are captured.
 * The help center and a legal page of the app are checked too. Demo data: seed_demo.
 */
const ADMIN = process.env.ADMIN_URL ?? "http://backend:8000";
const OWNER = { email: "proprio@solangeglow.test", password: "demo-Glow-2026" };
const SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP";
const LOOK = { theme: "light", textSize: "normal" } as const;

function base32(secret: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secret) bits += alphabet.indexOf(char).toString(2).padStart(5, "0");
  const bytes = bits.match(/.{8}/g) ?? [];
  return Buffer.from(bytes.map((byte) => parseInt(byte, 2)));
}

/** The code shown by an authenticator app (RFC 6238, 30 s, 6 digits). */
function totp(secret: string, at = Date.now()): string {
  const step = Buffer.alloc(8);
  step.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)));
  const digest = createHmac("sha1", base32(secret)).update(step).digest();
  const offset = digest[digest.length - 1]! & 0x0f;
  const number = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(number % 1_000_000).padStart(6, "0");
}

async function signInToAdmin(page: Page) {
  await page.goto(`${ADMIN}/admin/login/?next=/admin/`, { timeout: 120_000 });
  await page.locator("input[name=username]").fill(OWNER.email);
  await page.locator("input[name=password]").fill(OWNER.password);
  await page.locator("[type=submit]").first().click();
  await expect(page).toHaveURL(/\/admin\/2fa\//);
  await page.screenshot({ path: "e2e/screenshots/backoffice-2fa.png" });
  // A code is used only once: wait for the next one if this one may already be spent.
  if (Date.now() % 30_000 > 25_000) await page.waitForTimeout(6_000);
  await page.locator("input[name=code]").fill(totp(SECRET));
  await page.locator("input[name=code]").press("Enter");
  await expect(page).toHaveURL(/\/admin\/(\?.*)?$/);
}

test.use({ viewport: VIEWPORTS.desktop });

test("the owner signs in with two-factor and steers everything from the admin", async ({
  page,
}) => {
  test.setTimeout(600_000);
  await signInToAdmin(page);
  await expect(page.locator("canvas").first()).toBeVisible();
  await page.screenshot({ path: "e2e/screenshots/backoffice-dashboard.png", fullPage: true });

  const pages: [string, string][] = [
    ["/admin/consoles/moderation/", "backoffice-moderation"],
    ["/admin/consoles/disputes/", "backoffice-disputes"],
    ["/admin/consoles/selection/", "backoffice-selection"],
    ["/admin/team/", "backoffice-team"],
    ["/admin/features/", "backoffice-flags"],
    ["/admin/translations/?q=cherches&lang=fr", "backoffice-translations"],
    ["/admin/core/auditevent/", "backoffice-audit"],
    ["/admin/backoffice/prospect/", "backoffice-prospects"],
    ["/admin/content/page/", "backoffice-pages"],
    ["/admin/content/ticket/", "backoffice-tickets"],
  ];
  for (const [path, name] of pages) {
    const response = await page.goto(`${ADMIN}${path}`, { timeout: 120_000 });
    expect(response?.status(), path).toBe(200);
    await page.screenshot({ path: `e2e/screenshots/${name}.png`, fullPage: true });
  }
});

test.describe("help center of the app", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("the FAQ answers first, then the question goes to the team", async ({ page }) => {
    test.setTimeout(300_000);
    await page.goto("/fr/aide", { waitUntil: "load", timeout: 240_000 }).catch(() => undefined);
    await openWith(page, "/fr/aide", LOOK);
    await expect(page.getByRole("heading", { name: "Aide", level: 1 })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/help-center.png", fullPage: true });

    await page.getByLabel("Ta question").fill("Comment annuler un rendez-vous ?");
    await page.getByRole("button", { name: "Chercher une réponse" }).click();
    await expect(page.getByText("Ces réponses peuvent t'aider :")).toBeVisible();
    await page.getByRole("button", { name: "Non, écrire à l'équipe" }).click();
    await page.getByLabel("Ton prénom").fill("Awa");
    await page.getByLabel("Ton e-mail").fill("awa@example.com");
    await page.getByRole("button", { name: "Envoyer ma question" }).click();
    await expect(page.getByRole("heading", { name: "Question envoyée" })).toBeVisible();
    await page.screenshot({ path: "e2e/screenshots/help-sent.png" });
  });

  test("a legal page is readable", async ({ page }) => {
    await openWith(page, "/fr/pages/conditions-generales", LOOK);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoSeriousA11yIssue(page);
    await page.screenshot({ path: "e2e/screenshots/help-terms.png", fullPage: true });
  });
});
