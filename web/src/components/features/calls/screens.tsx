"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Downloaded when opened (ADR-004): the call screen brings LiveKit with it.
const loading = () => <Skeleton className="rounded-card m-4 h-80" />;

export const CallScreen = dynamic(() => import("./call-screen").then((m) => m.CallScreen), {
  loading,
  ssr: false,
});
export const CallLog = dynamic(() => import("./call-log").then((m) => m.CallLog), { loading });
