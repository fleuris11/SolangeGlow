/**
 * Demonstration content for the public home page, until real pros join.
 * Names and places are content (not translated); trade keys and labels are translated.
 * Amounts are integers in the smallest unit of the currency, like everywhere else.
 */
import type { Look, Outfit, Skin } from "@/components/features/illustrations/portrait";
import type { Trade } from "@/components/features/trades/trade-icon";

export type DemoPro = {
  id: string;
  name: string;
  trade: Trade;
  district: string;
  city: string;
  /** Next free slot today, 24 h clock. */
  nextSlot: { hour: number; minute: number };
  fromAmountMinor: number;
  currency: "XOF" | "EUR";
  rating: number;
  reviews: number;
  verified: boolean;
  portrait: { skin: Skin; look: Look; outfit: Outfit; accent?: "hibiscus" | "or" | "feuille" };
};

export const DEMO_PROS: DemoPro[] = [
  {
    id: "aicha",
    name: "Aïcha",
    trade: "braids",
    district: "Fidjrossè",
    city: "Cotonou",
    nextSlot: { hour: 14, minute: 0 },
    fromAmountMinor: 8000,
    currency: "XOF",
    rating: 4.9,
    reviews: 128,
    verified: true,
    portrait: { skin: 4, look: "braids", outfit: "or" },
  },
  {
    id: "gloria",
    name: "Gloria",
    trade: "makeup",
    district: "Akpakpa",
    city: "Cotonou",
    nextSlot: { hour: 15, minute: 30 },
    fromAmountMinor: 10000,
    currency: "XOF",
    rating: 4.8,
    reviews: 86,
    verified: true,
    portrait: { skin: 3, look: "makeup", outfit: "hibiscus" },
  },
  {
    id: "senami",
    name: "Sènami",
    trade: "hair",
    district: "Godomey",
    city: "Abomey-Calavi",
    nextSlot: { hour: 16, minute: 0 },
    fromAmountMinor: 5000,
    currency: "XOF",
    rating: 4.7,
    reviews: 54,
    verified: false,
    portrait: { skin: 5, look: "bun", outfit: "feuille" },
  },
  {
    id: "nafissatou",
    name: "Nafissatou",
    trade: "headwrap",
    district: "Zogbo",
    city: "Cotonou",
    nextSlot: { hour: 17, minute: 0 },
    fromAmountMinor: 3000,
    currency: "XOF",
    rating: 5,
    reviews: 41,
    verified: true,
    portrait: { skin: 4, look: "headwrap", outfit: "prune", accent: "or" },
  },
  {
    id: "rachida",
    name: "Rachida",
    trade: "nails",
    district: "Cadjèhoun",
    city: "Cotonou",
    nextSlot: { hour: 18, minute: 0 },
    fromAmountMinor: 6000,
    currency: "XOF",
    rating: 4.6,
    reviews: 73,
    verified: true,
    portrait: { skin: 2, look: "afro", outfit: "hibiscus" },
  },
  {
    id: "clarisse",
    name: "Clarisse",
    trade: "skincare",
    district: "Château-Rouge",
    city: "Paris",
    nextSlot: { hour: 11, minute: 0 },
    fromAmountMinor: 3500,
    currency: "EUR",
    rating: 4.9,
    reviews: 212,
    verified: true,
    portrait: { skin: 3, look: "natural", outfit: "feuille" },
  },
];

export type ShelfKey = "smallPrices" | "trending" | "luxury";

export const DEMO_GIFT = {
  fromAmountMinor: 1500,
  currency: "EUR" as const,
  city: "Cotonou",
};

export const CITIES = ["Cotonou", "Abomey-Calavi", "Porto-Novo", "Parakou", "Paris", "Lyon"];
