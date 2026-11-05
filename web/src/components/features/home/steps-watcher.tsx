"use client";

import { useEffect } from "react";

/** Sets the state of the pinned piece of product from the sentence being read. No script, first state. */
export function StepsWatcher({ target }: { target: string }) {
  useEffect(() => {
    const root = document.getElementById(target);
    if (!root || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            root.dataset.active = (entry.target as HTMLElement).dataset.step;
          }
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    root.querySelectorAll("[data-step]").forEach((step) => observer.observe(step));
    return () => observer.disconnect();
  }, [target]);
  return null;
}
