"use client";

import { useEffect, type CSSProperties } from "react";

import { cn } from "@/lib/cn";

type Props = {
  /** Accessible text announcing what succeeded ("Payment received"). */
  label: string;
  size?: number;
  className?: string;
};

const PETALS = [-62, 0, 62];

/**
 * The "éclosion": three petals open around a check mark (600 ms), with a light vibration.
 * Reserved for important successes: payment, confirmed booking, receipt code accepted.
 */
export function Bloom({ label, size = 120, className }: Props) {
  useEffect(() => {
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!reduced) navigator.vibrate?.(30);
  }, []);

  return (
    <span
      role="img"
      aria-label={label}
      className={cn("relative inline-flex shrink-0 items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      {PETALS.map((angle, index) => (
        <span
          key={angle}
          aria-hidden
          className={cn(
            "petal absolute top-[6%] left-[34%] h-[44%] w-[32%] origin-[50%_100%]",
            index === 1 ? "bg-hibiscus" : "bg-or",
          )}
          style={
            {
              "--petal-angle": `${angle}deg`,
              transform: `rotate(${angle}deg)`,
              animation: "petal-open 600ms var(--ease-out-soft) both",
            } as CSSProperties
          }
        />
      ))}
      <span
        aria-hidden
        className="bg-feuille relative inline-flex size-[46%] items-center justify-center rounded-full"
      >
        <svg viewBox="0 0 24 24" className="size-[60%]" fill="none">
          <path
            d="M5 12.5l4.5 4.5L19 7.5"
            stroke="var(--lait)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="24"
            strokeDashoffset="24"
            style={{ animation: "check-draw 300ms 300ms var(--ease-out-soft) forwards" }}
          />
        </svg>
      </span>
    </span>
  );
}
