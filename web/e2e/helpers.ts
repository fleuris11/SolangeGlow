import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export const VIEWPORTS = {
  mobile: { width: 360, height: 740 },
  desktop: { width: 1280, height: 800 },
} as const;

export type Theme = "light" | "dark";
export type TextSize = "normal" | "xlarge";

/** Opens a page with the given theme and text size, as a returning visitor would have saved. */
export async function openWith(
  page: Page,
  path: string,
  { theme, textSize }: { theme: Theme; textSize: TextSize },
) {
  await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
  await page.addInitScript(
    ([t, s]) => {
      // Only on the first load, so choices made during the test survive a reload.
      if (!window.localStorage.getItem("sg.preferences")) {
        window.localStorage.setItem("sg.preferences", JSON.stringify({ theme: t, textSize: s }));
      }
    },
    [theme, textSize] as const,
  );
  await page.goto(path, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
}

/** No serious or critical accessibility violation (WCAG 2.2 AA) on the current page. */
export async function expectNoSeriousA11yIssue(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const serious = results.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact ?? ""),
  );
  expect(
    serious,
    JSON.stringify(
      serious.map((v) => [v.id, v.nodes[0]?.target, v.nodes[0]?.failureSummary]),
      null,
      2,
    ),
  ).toEqual([]);
}

const API_HEADERS = { "X-SG-Client": "web" };

async function lastCode(page: Page, phone: string): Promise<string> {
  const response = await page.request.get(
    `/api/v1/dev/last-code?destination=${encodeURIComponent(phone)}`,
  );
  return response.ok() ? ((await response.json()).code as string) : "";
}

/** Signs in through the API with the code read on the dev endpoint (cookies of the page). */
export async function signInWithPhone(page: Page, phone: string) {
  const before = await lastCode(page, phone);
  const asked = await page.request.post("/api/v1/auth/otp/request", {
    data: { phone },
    headers: API_HEADERS,
  });
  expect(asked.ok(), await asked.text()).toBe(true);
  const { challenge_id } = await asked.json();
  let code = "";
  await expect
    .poll(
      async () => {
        code = await lastCode(page, phone);
        return /^\d{6}$/.test(code) && code !== before;
      },
      { timeout: 30_000, message: "new code sent by the worker (dev endpoint)" },
    )
    .toBe(true);
  const verified = await page.request.post("/api/v1/auth/otp/verify", {
    data: { challenge_id, code },
    headers: API_HEADERS,
  });
  expect(verified.ok()).toBe(true);
}

/** A new client, signed in and welcomed (adult, in Cotonou). */
export async function signInAsNewClient(page: Page, firstName?: string) {
  const phone = `+2290197${String(Math.floor(Math.random() * 1_000_000)).padStart(6, "0")}`;
  await signInWithPhone(page, phone);
  const onboarded = await page.request.post("/api/v1/me/onboarding", {
    data: { mode: "client", birth_date: "1995-04-12", city: "Cotonou" },
    headers: API_HEADERS,
  });
  expect(onboarded.ok()).toBe(true);
  if (firstName) {
    const named = await page.request.patch("/api/v1/me", {
      data: { first_name: firstName },
      headers: API_HEADERS,
    });
    expect(named.ok()).toBe(true);
  }
}
