import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests: screenshots for visual review and axe accessibility checks.
 * Run inside Docker: `docker compose run --rm e2e` (the web service must be up).
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    ...devices["Desktop Chrome"],
    navigationTimeout: 120_000,
  },
});
