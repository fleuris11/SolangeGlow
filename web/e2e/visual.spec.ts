import { expect, test } from "@playwright/test";

import { openWith, VIEWPORTS, type TextSize, type Theme } from "./helpers";

const PAGES = [
  { name: "home", path: "/fr" },
  { name: "design", path: "/fr/design" },
];
const THEMES: Theme[] = ["light", "dark"];
const TEXT_SIZES: TextSize[] = ["normal", "xlarge"];

/** Full-page screenshots for visual review, in e2e/screenshots/. */
for (const { name, path } of PAGES) {
  for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
    for (const theme of THEMES) {
      for (const textSize of TEXT_SIZES) {
        const id = `${name}-${viewportName}-${theme}-${textSize}`;
        test(`screenshot ${id}`, async ({ page }) => {
          await page.setViewportSize(viewport);
          await openWith(page, path, { theme, textSize });

          // Nothing may overflow horizontally.
          const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
          );
          expect(overflow, `${id} overflows horizontally`).toBeLessThanOrEqual(0);

          await page.screenshot({ path: `e2e/screenshots/${id}.png`, fullPage: true });
        });
      }
    }
  }
}
