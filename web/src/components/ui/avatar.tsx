import Image from "next/image";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Size = "sm" | "md" | "lg" | "xl";

const sizes: Record<Size, { box: string; px: number; text: string }> = {
  sm: { box: "size-10", px: 40, text: "text-small" },
  md: { box: "size-16", px: 64, text: "text-lead" },
  lg: { box: "size-24", px: 96, text: "text-headline" },
  xl: { box: "size-32", px: 128, text: "text-display" },
};

type Props = {
  name: string;
  src?: string;
  /** Custom picture (e.g. an illustration) used when there is no photo. */
  picture?: ReactNode;
  size?: Size;
  /** Glow halo: the pro has a story or a free slot today. Pulses once when shown. */
  halo?: boolean;
  className?: string;
};

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

/** Profile picture cut in the lotus petal shape, with the optional Glow halo. */
export function Avatar({ name, src, picture, size = "md", halo = false, className }: Props) {
  const { box, px, text } = sizes[size];

  const content = src ? (
    <Image
      src={src}
      alt={name}
      width={px}
      height={px}
      // Profile photos are already resized and re-encoded by the backend.
      unoptimized
      className="size-full object-cover"
    />
  ) : picture ? (
    <span role="img" aria-label={name} className="block size-full">
      {picture}
    </span>
  ) : (
    <span
      role="img"
      aria-label={name}
      className={cn("font-display flex size-full items-center justify-center font-bold", text)}
    >
      {initials(name)}
    </span>
  );

  const face = (
    <span className={cn("petal bg-poudre text-hibiscus block overflow-hidden", box)}>
      {content}
    </span>
  );

  if (!halo) return <span className={cn("inline-block shrink-0", className)}>{face}</span>;

  return (
    <span className={cn("relative inline-block shrink-0 p-[5px]", className)} data-halo>
      <span
        aria-hidden
        className="petal animate-halo absolute inset-0 bg-[conic-gradient(from_200deg,var(--hibiscus),var(--or),var(--hibiscus))]"
      />
      <span aria-hidden className="petal bg-lait absolute inset-[3px]" />
      <span className="relative block">{face}</span>
    </span>
  );
}
