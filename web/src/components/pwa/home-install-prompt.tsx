"use client";

import dynamic from "next/dynamic";

// The invitation is downloaded after the first paint (ADR-004): most visits never show it.
const InstallPrompt = dynamic(() => import("./install-prompt").then((m) => m.InstallPrompt), {
  ssr: false,
});

/** From the 3rd visit, when the browser offers to install the app. */
export function HomeInstallPrompt() {
  return <InstallPrompt moment="visits" icon={null} />;
}
