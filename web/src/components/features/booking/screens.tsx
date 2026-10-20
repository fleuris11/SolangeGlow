"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

// Each screen is downloaded when it is opened (ADR-004).
const loading = () => <Skeleton className="rounded-card h-80" />;

export const AppointmentsScreen = dynamic(
  () => import("./appointment-view").then((m) => m.AppointmentsScreen),
  { loading },
);
export const AppointmentView = dynamic(
  () => import("./appointment-view").then((m) => m.AppointmentView),
  { loading },
);
export const GroupView = dynamic(() => import("./group-view").then((m) => m.GroupView), {
  loading,
});
export const AgendaScreen = dynamic(() => import("./agenda").then((m) => m.AgendaScreen), {
  loading,
});
export const AgendaSettingsScreen = dynamic(
  () => import("./agenda-settings").then((m) => m.AgendaSettingsScreen),
  { loading },
);
export const ClientFilesScreen = dynamic(
  () => import("./client-files").then((m) => m.ClientFilesScreen),
  { loading },
);
