"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const SpecialRequests = dynamic(() => import("./requests").then((m) => m.SpecialRequests), {
  loading,
});
export const SelectionOrders = dynamic(() => import("./tracking").then((m) => m.SelectionOrders), {
  loading,
});
export const SelectionTracking = dynamic(
  () => import("./tracking").then((m) => m.SelectionTracking),
  { loading },
);
