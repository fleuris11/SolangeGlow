import type { ReactNode } from "react";

/** The seven trades at launch. The same pictograms are used everywhere (search, profiles, filters). */
export const TRADES = [
  "makeup",
  "hair",
  "braids",
  "nails",
  "sewing",
  "headwrap",
  "skincare",
] as const;

export type Trade = (typeof TRADES)[number];

/*
 * Drawn on Phosphor's 256 grid in its duotone style (16 px round strokes, 20 % fill),
 * so they sit naturally next to the Phosphor icons.
 */
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 16,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;
const tint = { fill: "currentColor", opacity: 0.2 } as const;

const drawings: Record<Trade, ReactNode> = {
  makeup: (
    <>
      <path d="M104 104V60l48-28v72Z" {...tint} />
      <path d="M104 104V60l48-28v72" {...stroke} />
      <rect x="92" y="104" width="72" height="32" rx="6" {...stroke} />
      <rect x="84" y="136" width="88" height="88" rx="10" {...stroke} />
    </>
  ),
  hair: (
    <>
      <rect x="36" y="64" width="184" height="48" rx="16" {...tint} />
      <rect x="36" y="64" width="184" height="48" rx="16" {...stroke} />
      {[60, 92, 124, 156, 188].map((x) => (
        <path key={x} d={`M${x + 8} 112v80`} {...stroke} />
      ))}
    </>
  ),
  braids: (
    <>
      {[0, 1, 2, 3].map((i) => (
        <ellipse
          key={i}
          cx={i % 2 ? 140 : 116}
          cy={52 + i * 40}
          rx="22"
          ry="30"
          transform={`rotate(${i % 2 ? 28 : -28} ${i % 2 ? 140 : 116} ${52 + i * 40})`}
          {...(i % 2 ? tint : { fill: "none" })}
        />
      ))}
      {[0, 1, 2, 3].map((i) => (
        <ellipse
          key={`s${i}`}
          cx={i % 2 ? 140 : 116}
          cy={52 + i * 40}
          rx="22"
          ry="30"
          transform={`rotate(${i % 2 ? 28 : -28} ${i % 2 ? 140 : 116} ${52 + i * 40})`}
          {...stroke}
        />
      ))}
      <path d="M128 196v28M112 224l16-12 16 12" {...stroke} />
    </>
  ),
  nails: (
    <>
      <rect x="68" y="120" width="120" height="104" rx="28" {...tint} />
      <rect x="68" y="120" width="120" height="104" rx="28" {...stroke} />
      <path d="M104 120V96h48v24" {...stroke} />
      <rect x="108" y="32" width="40" height="64" rx="10" {...stroke} />
      <path d="M100 168h56" {...stroke} />
    </>
  ),
  sewing: (
    <>
      <rect x="88" y="64" width="80" height="128" {...tint} />
      <rect x="60" y="40" width="136" height="24" rx="10" {...stroke} />
      <rect x="60" y="192" width="136" height="24" rx="10" {...stroke} />
      <path d="M88 64v128M168 64v128M88 100l80-16M88 140l80-16M88 180l80-16" {...stroke} />
    </>
  ),
  headwrap: (
    <>
      <path d="M60 140c-14-56 30-104 68-76 38-28 82 20 68 76Z" {...tint} />
      <path d="M60 140c-14-56 30-104 68-76 38-28 82 20 68 76Z" {...stroke} />
      <path d="M128 64v52M92 92l20 32M164 92l-20 32" {...stroke} />
      <path d="M84 148a44 44 0 0 0 88 0" {...stroke} />
    </>
  ),
  skincare: (
    <>
      <rect x="52" y="124" width="152" height="92" rx="22" {...tint} />
      <rect x="52" y="124" width="152" height="92" rx="22" {...stroke} />
      <rect x="44" y="92" width="168" height="32" rx="12" {...stroke} />
      <path d="M176 24v40M156 44h40" {...stroke} />
    </>
  ),
};

type Props = { trade: Trade; size?: number; className?: string };

/** Pictogram of a trade. Decorative: always shown next to the trade's name. */
export function TradeIcon({ trade, size = 32, className }: Props) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 256 256"
      width={size}
      height={size}
      className={className}
      focusable="false"
    >
      {drawings[trade]}
    </svg>
  );
}
