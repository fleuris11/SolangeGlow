"use client";

import { useEffect, useState, type ComponentType } from "react";

export const SPLASH_KEY = "sg_splash_day";

function today() {
  return new Date().toISOString().slice(0, 10);
}

/** The launch screen, at most once a day: the screen itself is downloaded only then. */
export function SplashLoader() {
  const [Screen, setScreen] = useState<ComponentType<{ onClose: () => void }> | null>(null);
  useEffect(() => {
    let seen: string | null = null;
    try {
      seen = window.localStorage.getItem(SPLASH_KEY);
    } catch {
      return; // no storage (private mode): no launch screen rather than one each time
    }
    if (seen === today()) return;
    try {
      window.localStorage.setItem(SPLASH_KEY, today());
    } catch {
      return;
    }
    void import("./splash").then((module) => setScreen(() => module.SplashAd));
  }, []);
  return Screen ? <Screen onClose={() => setScreen(null)} /> : null;
}
