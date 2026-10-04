import { Atkinson_Hyperlegible_Next, Fraunces } from "next/font/google";

/** Big moments only (welcome title, pro names, success screens, paid amounts). */
export const fraunces = Fraunces({
  subsets: ["latin", "latin-ext"],
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
  variable: "--font-fraunces",
});

/** Everything else: built for maximum legibility. */
export const atkinson = Atkinson_Hyperlegible_Next({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-atkinson",
  // Next.js has no fallback metrics for this recent font yet.
  adjustFontFallback: false,
});
