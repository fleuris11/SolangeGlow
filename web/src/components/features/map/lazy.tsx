"use client";

/** Maps load MapLibre only when they are shown (ADR-004). Import maps from here. */
import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

const loading = () => <Skeleton className="rounded-card h-72 w-full" />;

export const PointMap = dynamic(() => import("./point-map").then((m) => m.PointMap), {
  ssr: false,
  loading,
});

export const ExploreMap = dynamic(() => import("./explore-map").then((m) => m.ExploreMap), {
  ssr: false,
  loading,
});

export const LocationPicker = dynamic(
  () => import("./location-picker").then((m) => m.LocationPicker),
  { ssr: false, loading },
);

export const AreaEditor = dynamic(() => import("./area-editor").then((m) => m.AreaEditor), {
  ssr: false,
  loading,
});
