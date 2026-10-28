"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const OfferFlow = dynamic(() => import("./offer-flow").then((m) => m.OfferFlow), {
  loading,
});
export const GiftReception = dynamic(() => import("./reception").then((m) => m.GiftReception), {
  loading,
});
export const MyGifts = dynamic(() => import("./my-gifts").then((m) => m.MyGifts), { loading });
export const SentGiftDetail = dynamic(() => import("./my-gifts").then((m) => m.SentGiftDetail), {
  loading,
});
export const GlowCardPay = dynamic(() => import("./glow-card-pay").then((m) => m.GlowCardPay), {
  loading: () => null,
});
