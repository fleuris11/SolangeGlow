"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const MyPoints = dynamic(() => import("./my-points").then((m) => m.MyPoints), { loading });
export const DailyQuizScreen = dynamic(() => import("./quiz").then((m) => m.DailyQuizScreen), {
  loading,
});
export const WheelScreen = dynamic(() => import("./wheel").then((m) => m.WheelScreen), {
  loading,
});
export const PollsScreen = dynamic(() => import("./polls").then((m) => m.PollsScreen), {
  loading,
});
export const PollDetail = dynamic(() => import("./polls").then((m) => m.PollDetail), { loading });
export const PollCreate = dynamic(() => import("./polls").then((m) => m.PollCreate), { loading });
export const ChallengeScreen = dynamic(() => import("./challenge").then((m) => m.ChallengeScreen), {
  loading,
});
export const RoutineScreen = dynamic(() => import("./routine").then((m) => m.RoutineScreen), {
  loading,
});
export const CalendarScreen = dynamic(() => import("./calendar").then((m) => m.CalendarScreen), {
  loading,
});
export const RankingsScreen = dynamic(() => import("./calendar").then((m) => m.RankingsScreen), {
  loading,
});
