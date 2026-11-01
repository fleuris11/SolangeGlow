import type { Instrumentation } from "next";

import { errorEvent, SENTRY_DSN, storeUrl } from "@/lib/monitoring/errors";

/** Errors of the pages rendered by the server, sent to GlitchTip (off without a DSN). */
export const onRequestError: Instrumentation.onRequestError = async (error, request) => {
  const url = storeUrl(SENTRY_DSN);
  if (!url) return;
  const path = request.path.split("?")[0] ?? "/";
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(errorEvent(error as Error, path, "server")),
    });
  } catch {
    // GlitchTip unreachable: the error stays in the server logs.
  }
};
