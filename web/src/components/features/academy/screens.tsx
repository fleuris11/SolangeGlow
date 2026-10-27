"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const PlayerScreen = dynamic(() => import("./player-screen").then((m) => m.PlayerScreen), {
  loading,
});
export const QuizScreen = dynamic(() => import("./quiz-screen").then((m) => m.QuizScreen), {
  loading,
});
export const MyAcademyScreen = dynamic(
  () => import("./my-academy-screen").then((m) => m.MyAcademyScreen),
  { loading },
);
export const PassScreen = dynamic(() => import("./pass-screen").then((m) => m.PassScreen), {
  loading,
});
export const LivesScreen = dynamic(() => import("./lives-screen").then((m) => m.LivesScreen), {
  loading,
});
export const LiveRoomScreen = dynamic(
  () => import("./lives-screen").then((m) => m.LiveRoomScreen),
  { loading },
);
export const StudioScreen = dynamic(() => import("./studio-screen").then((m) => m.StudioScreen), {
  loading,
});
export const CourseEditor = dynamic(() => import("./course-editor").then((m) => m.CourseEditor), {
  loading,
});
