import { Figtree, League_Spartan } from "next/font/google";

/** Titles, names and amounts: a compact geometric, punchy in a few short words. */
export const displayFont = League_Spartan({
  subsets: ["latin", "latin-ext"],
  weight: "700",
  display: "swap",
  variable: "--font-display-face",
});

/** Everything else: open, friendly and very legible on a small screen. */
export const textFont = Figtree({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-text-face",
});
