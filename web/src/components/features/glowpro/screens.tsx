"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const PlanScreen = dynamic(() => import("./plan-screen").then((m) => m.PlanScreen), {
  loading,
});
export const DashboardScreen = dynamic(
  () => import("./dashboard-screen").then((m) => m.DashboardScreen),
  { loading },
);
export const StockScreen = dynamic(() => import("./stock-screen").then((m) => m.StockScreen), {
  loading,
});
export const CampaignsScreen = dynamic(
  () => import("./campaigns-screen").then((m) => m.CampaignsScreen),
  { loading },
);
export const GiftCardsScreen = dynamic(
  () => import("./gift-cards-screen").then((m) => m.GiftCardsScreen),
  { loading },
);
export const InvoicesScreen = dynamic(
  () => import("./invoices-screen").then((m) => m.InvoicesScreen),
  { loading },
);
export const SalonHub = dynamic(() => import("./salon-hub").then((m) => m.SalonHub), {
  loading,
});
export const PackagesScreen = dynamic(() => import("./salon-hub").then((m) => m.PackagesScreen), {
  loading,
});
export const OffersView = dynamic(() => import("./offers-view").then((m) => m.OffersView), {
  loading,
});
export const UnsubscribeScreen = dynamic(
  () => import("./unsubscribe-screen").then((m) => m.UnsubscribeScreen),
  { loading },
);
