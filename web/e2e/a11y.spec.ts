import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { openWith, VIEWPORTS, type Theme } from "./helpers";

const PATHS = ["/fr", "/en/explore", "/sk/messages", "/fr/me", "/fr/create", "/fr/design"];
const THEMES: Theme[] = ["light", "dark"];

/** No serious or critical accessibility violation, in light and dark, on mobile. */
for (const path of PATHS) {
  for (const theme of THEMES) {
    test(`axe ${path} ${theme}`, async ({ page }) => {
      await page.setViewportSize(VIEWPORTS.mobile);
      await openWith(page, path, { theme, textSize: "normal" });

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();
      const serious = results.violations
        .filter((v) => v.impact === "serious" || v.impact === "critical")
        .map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          targets: v.nodes.slice(0, 5).map((n) => `${n.target.join(" ")} :: ${n.failureSummary}`),
        }));

      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
    });
  }
}
