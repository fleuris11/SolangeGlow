"use client";

import { useEffect, useState } from "react";

/** Seconds left until `until` (a timestamp in ms), updated every second. */
export function useCountdown(until: number | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (until === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [until]);

  if (until === null) return 0;
  return Math.max(0, Math.ceil((until - now) / 1000));
}
