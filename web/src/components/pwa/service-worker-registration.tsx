"use client";

import { useEffect } from "react";

/**
 * Registers the service worker: offline cache + phone alerts in production;
 * phone alerts only in development (`?dev=1` turns the cache off, see public/sw.js).
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const url = process.env.NODE_ENV === "production" ? "/sw.js" : "/sw.js?dev=1";
    navigator.serviceWorker.register(url, { scope: "/" }).catch(() => undefined);
  }, []);

  return null;
}
