import type { Page } from "@playwright/test";

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
