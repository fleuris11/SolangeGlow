// The public home, for review: first screen and each section as a visitor scrolls to it, 360 and
// 1440, then a short video. A full-page shot would freeze the scroll effects halfway.
// docker compose run --rm --no-deps -T --entrypoint node e2e e2e/capture-home.mjs
import { mkdirSync, renameSync } from "node:fs";

import { chromium } from "@playwright/test";
import sharp from "sharp";

const OUT = process.env.OUT ?? "e2e/screenshots/home";
const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const SECTIONS = [
  "hands-title",
  "code-title",
  "booking-title",
  "more-title",
  "gift-title",
  "feed-title",
];
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();

async function shot(page, file) {
  const png = await page.screenshot({ type: "png" });
  await sharp(png).jpeg({ quality: 78 }).toFile(`${OUT}/${file}.jpg`);
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
    page.on("console", (message) => {
      if (message.type() === "error") console.log("console error", message.text().slice(0, 600));
    });
    page.on("pageerror", (error) => console.log("page error", error.message.slice(0, 600)));
    await page.goto(`${BASE}/fr`, { waitUntil: "load", timeout: 240_000 });
    await page.waitForTimeout(1500);
    await shot(page, `first-${size.width}-${theme}`);
    if (theme === "light") {
      for (const id of SECTIONS) {
        await page.evaluate((target) => {
          const box = document.getElementById(target).closest("section").getBoundingClientRect();
          window.scrollTo(0, box.top + window.scrollY);
        }, id);
        await page.waitForTimeout(2500);
        await shot(page, `${id.replace("-title", "")}-${size.width}`);
      }
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
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
