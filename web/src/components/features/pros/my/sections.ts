/** The parts of « Ma vitrine », each at /pro/<part>. */
export const SECTIONS = [
  "info",
  "services",
  "hours",
  "portfolio",
  "reviews",
  "messages",
  "place",
  "share",
  "verification",
] as const;

export type Section = (typeof SECTIONS)[number];
