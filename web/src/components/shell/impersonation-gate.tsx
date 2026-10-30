"use client";

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";

// Downloaded only while a team member is signed in as a member (module 12).
const ImpersonationBanner = dynamic(
  () => import("./impersonation-banner").then((m) => m.ImpersonationBanner),
  { ssr: false },
);

const COOKIE = /(?:^|;\s*)sg_impersonation=([^;]+)/;

function read(): string {
  return typeof document === "undefined" ? "" : (document.cookie.match(COOKIE)?.[1] ?? "");
}

const subscribe = () => () => {};

/** Shows the banner when the cookie set by the back office exists (it holds no secret). */
export function ImpersonationGate() {
  const raw = useSyncExternalStore(subscribe, read, () => "");
  return raw ? <ImpersonationBanner raw={raw} /> : null;
}
