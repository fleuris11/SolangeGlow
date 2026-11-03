import type { CSSProperties } from "react";

const PETALS = [-34, 0, 34];

/**
 * Three small petals flying off a like. Plain CSS: give it a new `key` to play it again.
 * Decorative: the button says what happened.
 */
export function LikeBurst() {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute inset-0 flex items-center justify-center"
    >
      {PETALS.map((angle) => (
        <span
          key={angle}
          className="sg-like-petal"
          style={{ "--angle": `${angle}deg` } as CSSProperties}
        />
      ))}
    </span>
  );
}
