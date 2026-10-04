/**
 * Illustrated portrait used as a placeholder until pros upload their own photos.
 * Several skin tones and styles, so before/after can be understood without reading.
 */
export type Skin = 1 | 2 | 3 | 4 | 5;
export type Look = "natural" | "afro" | "braids" | "headwrap" | "makeup" | "bun";
export type Outfit = "prune" | "feuille" | "or" | "hibiscus";

type Props = {
  skin: Skin;
  look: Look;
  outfit?: Outfit;
  /** Colour of the headwrap or of the makeup accent. */
  accent?: "hibiscus" | "or" | "feuille";
  className?: string;
};

const outfitColor: Record<Outfit, string> = {
  prune: "var(--prune-doux)",
  feuille: "var(--feuille)",
  or: "var(--or)",
  hibiscus: "var(--hibiscus)",
};

const HAIR = "var(--cheveux)";

export function Portrait({ skin, look, outfit = "prune", accent = "hibiscus", className }: Props) {
  const skinColor = `var(--peau-${skin})`;
  const accentColor = `var(--${accent})`;
  const styled = look !== "natural";

  return (
    <svg
      aria-hidden
      viewBox="0 0 120 120"
      preserveAspectRatio="xMidYMid slice"
      className={className ?? "block size-full"}
      focusable="false"
    >
      <rect width="120" height="120" fill="var(--poudre)" />

      {/* Hair behind the head */}
      {look === "afro" && <circle cx="60" cy="46" r="34" fill={HAIR} />}
      {look === "braids" && (
        <g stroke={HAIR} strokeWidth="5" strokeLinecap="round" strokeDasharray="4 2">
          {[36, 42, 48].map((x) => (
            <path key={x} d={`M${x} 44 C${x - 4} 70 ${x - 6} 92 ${x - 4} 112`} fill="none" />
          ))}
          {[72, 78, 84].map((x) => (
            <path key={x} d={`M${x} 44 C${x + 4} 70 ${x + 6} 92 ${x + 4} 112`} fill="none" />
          ))}
        </g>
      )}
      {look === "bun" && <circle cx="60" cy="22" r="11" fill={HAIR} />}

      {/* Neck and shoulders */}
      <rect x="52" y="70" width="16" height="20" fill={skinColor} />
      <path d="M14 120c2-22 22-34 46-34s44 12 46 34Z" fill={outfitColor[outfit]} />

      {/* Head */}
      <ellipse cx="60" cy="54" rx="18" ry="22" fill={skinColor} />

      {/* Hair in front */}
      {(look === "natural" || look === "afro" || look === "makeup") && (
        <path d="M41 52c-3-22 13-30 19-30s22 8 19 30c-4-12-12-16-19-16s-15 4-19 16Z" fill={HAIR} />
      )}
      {look === "braids" && (
        <g>
          <path
            d="M41 50c-2-20 12-28 19-28s21 8 19 28c-5-11-12-15-19-15s-14 4-19 15Z"
            fill={HAIR}
          />
          <path
            d="M50 26v12M60 23v12M70 26v12"
            stroke="var(--poudre)"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.6"
          />
        </g>
      )}
      {look === "bun" && (
        <path d="M41 50c-2-20 12-28 19-28s21 8 19 28c-5-11-12-15-19-15s-14 4-19 15Z" fill={HAIR} />
      )}
      {look === "headwrap" && (
        <g>
          <path
            d="M34 50C28 20 52 6 60 22c8-16 32-2 26 28-8-10-16-14-26-14s-18 4-26 14Z"
            fill={accentColor}
          />
          <path
            d="M60 22v14M46 18l8 16M74 18l-8 16"
            stroke="var(--lait)"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.55"
            fill="none"
          />
        </g>
      )}

      {/* Face: closed eyes, cheeks and lips */}
      <path
        d="M50 55q3 2 6 0M64 55q3 2 6 0"
        stroke={HAIR}
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
      />
      {look === "makeup" && (
        <>
          <ellipse cx="48" cy="62" rx="4.5" ry="2.5" fill={accentColor} opacity="0.35" />
          <ellipse cx="72" cy="62" rx="4.5" ry="2.5" fill={accentColor} opacity="0.35" />
          <path d="M49 53q4-3 8 0M63 53q4-3 8 0" stroke="var(--or)" strokeWidth="1.6" fill="none" />
        </>
      )}
      <ellipse
        cx="60"
        cy="66"
        rx="5"
        ry="2.2"
        fill={look === "makeup" ? "var(--hibiscus)" : HAIR}
        opacity={look === "makeup" ? 1 : 0.45}
      />

      {/* Earrings once styled */}
      {styled && (
        <>
          <circle cx="42" cy="62" r="2.4" fill="var(--or)" />
          <circle cx="78" cy="62" r="2.4" fill="var(--or)" />
        </>
      )}
    </svg>
  );
}
