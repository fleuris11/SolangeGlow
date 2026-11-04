"use client";

import dynamic from "next/dynamic";
import { useSyncExternalStore, type ReactNode } from "react";

import { hasSession } from "@/lib/api/client";

const ProSwitch = dynamic(() => import("./pro-switch").then((m) => m.ProSwitch));
const nothing = () => () => undefined;

/** Only someone signed in downloads the way to her activity (ADR-004). */
export function ProSwitchLoader({ icon }: { icon: ReactNode }) {
  const signedIn = useSyncExternalStore(nothing, hasSession, () => false);
  return signedIn ? <ProSwitch icon={icon} /> : null;
}
