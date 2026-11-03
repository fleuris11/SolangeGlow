"use client";

import { useTranslations } from "next-intl";
import { useRef, useState, type ReactNode, type TouchEvent } from "react";

type Props = {
  onRefresh: () => Promise<unknown> | void;
  children: ReactNode;
};

const THRESHOLD = 72;
const MAX_PULL = 110;
// Past the threshold the finger moves further than the petal: it slows down, it never stops.
const FRICTION = 0.5;

/**
 * Pull down from the top of the page: a petal opens with the gesture, then the page refreshes.
 * Only with a finger at the very top. It adds nothing that the page does not already offer.
 */
export function PullToRefresh({ onRefresh, children }: Props) {
  const t = useTranslations("ui.pull");
  const start = useRef<number | null>(null);
  const [distance, setDistance] = useState(0);
  const [busy, setBusy] = useState(false);

  function onTouchStart(event: TouchEvent) {
    if (window.scrollY > 0 || busy || event.touches.length > 1) return;
    start.current = event.touches[0]?.clientY ?? null;
  }

  function onTouchMove(event: TouchEvent) {
    if (start.current === null) return;
    const pulled = (event.touches[0]?.clientY ?? 0) - start.current;
    setDistance(pulled > 0 ? Math.min(pulled * FRICTION, MAX_PULL) : 0);
  }

  async function onTouchEnd() {
    const reached = distance >= THRESHOLD;
    start.current = null;
    setDistance(0);
    if (!reached) return;
    setBusy(true);
    try {
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }

  const progress = Math.min(distance / THRESHOLD, 1);

  return (
    <div onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}>
      <div
        aria-hidden
        className="flex justify-center overflow-hidden"
        style={{ height: busy ? 48 : distance }}
      >
        <span
          className="bg-hibiscus sg-petal-shape mt-2 block size-8"
          style={{
            transform: `scale(${busy ? 1 : progress}) rotate(${progress * 180}deg)`,
            opacity: busy ? 1 : progress,
          }}
        />
      </div>
      <span role="status" className="sr-only">
        {busy ? t("busy") : ""}
      </span>
      {children}
    </div>
  );
}
