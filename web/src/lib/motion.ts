/**
 * Durations and curves of the interface, the same values as tokens.css (solange-design,
 * emil-design-eng). For the few animations played from script (Web Animations API).
 */
export const DURATION = {
  /** Press, toggle, tick. */
  micro: 160,
  /** Always faster than the way in. */
  exit: 160,
  /** Sheet, menu, card that grows. */
  opening: 280,
  /** Signature moments, once per journey. */
  signature: 600,
} as const;

export const EASING = {
  /** Things entering or reacting: starts fast, so it feels instant. */
  out: "cubic-bezier(0.23, 1, 0.32, 1)",
  /** Things moving from one place to another on the screen. */
  move: "cubic-bezier(0.77, 0, 0.175, 1)",
  /** Sheets that slide (iOS curve). */
  sheet: "cubic-bezier(0.32, 0.72, 0, 1)",
} as const;

/** A flick dismisses whatever the distance (pixels per millisecond). */
export const FLICK_VELOCITY = 0.11;

/** The phone's setting or the profile's « Reduced animations ». */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return (
    document.documentElement.dataset.motion === "reduced" ||
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}
