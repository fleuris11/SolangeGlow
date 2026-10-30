"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Downloaded when the screen is opened (ADR-004).
export const BoostScreen = dynamic(() => import("./boost-screen").then((m) => m.BoostScreen), {
  loading: () => <Skeleton className="rounded-card h-80" />,
});
