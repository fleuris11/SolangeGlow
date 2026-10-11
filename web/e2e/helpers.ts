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
