import { Gloock, Hanken_Grotesk } from "next/font/google";

/** Titles and big moments. Close to the contrast of the logo, readable over a photo. */
export const displayFont = Gloock({
  subsets: ["latin", "latin-ext"],
  weight: "400",
  display: "swap",
  variable: "--font-display-face",
});

/** Everything else: plain and very legible, with a plain zero for prices. */
export const textFont = Hanken_Grotesk({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-text-face",
});
