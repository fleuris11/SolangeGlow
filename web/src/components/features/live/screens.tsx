"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Downloaded when opened (ADR-004): the live room brings LiveKit with it.
export const LiveRoom = dynamic(() => import("./live-room").then((m) => m.LiveRoom), {
  loading: () => <Skeleton className="rounded-card m-4 h-96" />,
  ssr: false,
});
