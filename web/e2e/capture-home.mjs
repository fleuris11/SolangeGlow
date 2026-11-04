// The public home, for review: first screen and whole page, 360 and 1440, then a short video.
// docker compose run --rm --no-deps -T --entrypoint node e2e e2e/capture-home.mjs
import { mkdirSync, renameSync } from "node:fs";

import { chromium } from "@playwright/test";
import sharp from "sharp";

const OUT = process.env.OUT ?? "e2e/screenshots/home";
const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const FULL_WIDTH = { 360: 360, 1440: 1000 };
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();

async function shot(page, file, fullPage = false, width) {
  const png = await page.screenshot({ fullPage, type: "png" });
  const image = sharp(png, { limitInputPixels: false });
  // JPEG: a whole page can be too tall for WebP.
  await (width ? image.resize(width) : image).jpeg({ quality: 78 }).toFile(`${OUT}/${file}.jpg`);
}

for (const size of [
  { width: 360, height: 740 },
  { width: 1440, height: 900 },
]) {
  for (const theme of ["light", "dark"]) {
    const context = await browser.newContext({ viewport: size, colorScheme: theme });
    await context.addInitScript(
      ([value]) => {
        localStorage.setItem("sg.preferences", JSON.stringify({ theme: value }));
        localStorage.setItem("sg.privacy-notice", "1");
      },
      [theme],
    );
    const page = await context.newPage();
    await page.goto(`${BASE}/fr`, { waitUntil: "load", timeout: 240_000 });
    await page.waitForTimeout(1500);
    await shot(page, `first-${size.width}-${theme}`);
    if (theme === "light") {
      // Lazy pictures and scroll effects: go down the page like a visitor.
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y < height; y += size.height * 0.8) {
        await page.evaluate((top) => window.scrollTo(0, top), y);
        await page.waitForTimeout(900);
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      await shot(page, `page-${size.width}-${theme}`, true, FULL_WIDTH[size.width]);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      console.log(size.width, "sideways overflow", overflow, "height", height);
    }
    await context.close();
  }
}

// Very large text on a phone, and the trade chooser.
{
  const context = await browser.newContext({ viewport: { width: 360, height: 740 } });
  await context.addInitScript(() => {
    localStorage.setItem("sg.preferences", JSON.stringify({ textSize: "xlarge" }));
    localStorage.setItem("sg.privacy-notice", "1");
  });
  const page = await context.newPage();
  await page.goto(`${BASE}/fr`, { waitUntil: "load", timeout: 240_000 });
  await page.waitForTimeout(800);
  await shot(page, "first-360-xlarge");
  console.log(
    "xlarge overflow",
    await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
  );
  await page.getByText("Tresses", { exact: true }).first().click();
  await page.waitForTimeout(1200);
  await shot(page, "first-360-braids");
  await context.close();
}

// Video: the opening, then the scroll.
for (const size of [
  { width: 360, height: 740 },
  { width: 1440, height: 900 },
]) {
  const context = await browser.newContext({
    viewport: size,
    recordVideo: { dir: `${OUT}/tmp`, size },
  });
  await context.addInitScript(() => localStorage.setItem("sg.privacy-notice", "1"));
  const page = await context.newPage();
  await page.goto(`${BASE}/fr`, { waitUntil: "load", timeout: 240_000 });
  await page.waitForTimeout(1200);
  await page.getByText("Tresses", { exact: true }).first().click();
  await page.waitForTimeout(900);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const steps = 90;
  for (let step = 1; step <= steps; step += 1) {
    await page.evaluate((top) => window.scrollTo(0, top), ((height * 0.7) / steps) * step);
    await page.waitForTimeout(90);
  }
  const video = page.video();
  await context.close();
  if (video) renameSync(await video.path(), `${OUT}/home-${size.width}.webm`);
}
await browser.close();
console.log("done");
