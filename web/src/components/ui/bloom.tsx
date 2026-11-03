"use client";

import { useEffect, type CSSProperties } from "react";

import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/lib/motion";

type Props = {
  /** Accessible text announcing what succeeded ("Payment received"). */
  label: string;
  size?: number;
  className?: string;
};

const PETALS = [
  { angle: 0, fill: "var(--hibiscus)", delay: 0 },
  { angle: 120, fill: "var(--or)", delay: 60 },
  { angle: 240, fill: "var(--hibiscus-press)", delay: 120 },
];
const PETAL_PATH = "M50 6C68 22 68 38 50 52 32 38 32 22 50 6Z";

/**
 * The "éclosion": three petals open around a check mark (600 ms), with a light vibration.
 * Reserved for important successes: payment, confirmed booking, receipt code accepted.
 * The result is complete at once with reduced animations: the check never depends on it.
 */
export function Bloom({ label, size = 120, className }: Props) {
  useEffect(() => {
    if (!prefersReducedMotion()) navigator.vibrate?.(30);
  }, []);

  return (
    <span
      role="img"
      aria-label={label}
      className={cn("relative inline-flex shrink-0", className)}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" className="size-full overflow-visible" fill="none" aria-hidden>
        {PETALS.map(({ angle, fill, delay }) => (
          <g key={angle} transform={`rotate(${angle} 50 50)`}>
            <path
              d={PETAL_PATH}
              fill={fill}
              className="sg-bloom-petal"
              style={{ animationDelay: `${delay}ms` } as CSSProperties}
            />
          </g>
        ))}
        <circle cx="50" cy="50" r="17" fill="var(--feuille)" />
        <path
          d="M42 50.5l6 6 11-12"
          stroke="var(--lait)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray="28"
          strokeDashoffset="28"
          className="sg-bloom-check"
        />
      </svg>
    </span>
  );
}
