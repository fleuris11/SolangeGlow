import { CrownSimple, SealCheck, Sparkle, Star } from "@phosphor-icons/react/dist/ssr";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "glow" | "star" | "icon" | "verified";

const tones: Record<BadgeTone, { className: string; icon: ReactNode }> = {
  glow: { className: "bg-poudre text-prune", icon: <Sparkle weight="duotone" size={16} /> },
  star: { className: "bg-or text-sur-or", icon: <Star weight="fill" size={16} /> },
  icon: {
    className: "border-2 border-or bg-carte text-prune",
    icon: <CrownSimple weight="fill" size={16} className="text-or" />,
  },
  verified: {
    className: "bg-feuille text-lait",
    icon: <SealCheck weight="fill" size={16} />,
  },
};

type Props = { tone: BadgeTone; children: ReactNode; className?: string };

/** Levels (Glow, Star, Icône) and the "verified pro" mark: icon + word, never colour alone. */
export function Badge({ tone, children, className }: Props) {
  const { className: toneClass, icon } = tones[tone];
  return (
    <span
      className={cn(
        "text-mention inline-flex items-center gap-1 rounded-full px-3 py-1 font-bold",
        toneClass,
        className,
      )}
    >
      <span aria-hidden className="inline-flex">
        {icon}
      </span>
      {children}
    </span>
  );
}
