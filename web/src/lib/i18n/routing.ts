import { defineRouting } from "next-intl/routing";

// Add a language here (plus its file in src/messages/) to make it available.
export const routing = defineRouting({
  locales: ["fr", "en", "sk"],
  defaultLocale: "fr",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];
