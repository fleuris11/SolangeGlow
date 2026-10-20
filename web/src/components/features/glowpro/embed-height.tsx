"use client";

import { useEffect } from "react";

/** Tells the salon's website how tall the booking is (its frame follows). */
export function EmbedHeight() {
  useEffect(() => {
    if (window.parent === window) return;
    const send = () =>
      window.parent.postMessage(
        { type: "solangeglow:height", height: document.documentElement.scrollHeight },
        "*",
      );
    const observer = new ResizeObserver(send);
    observer.observe(document.body);
    send();
    return () => observer.disconnect();
  }, []);
  return null;
}
