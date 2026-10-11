import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // Docker on Windows is slow under load: user journeys get more than the default 5 s.
    testTimeout: 15_000,
    // Let Vite resolve next-intl's imports of next/navigation (mocked in setup.ts).
    server: { deps: { inline: ["next-intl"] } },
  },
});
