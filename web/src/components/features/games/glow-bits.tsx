import { Fire } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import type { GlowLevel, ProLevel } from "@/lib/api/games";
import { cn } from "@/lib/cn";

/** The flame of the streak: days in a row, gone (grey, « 0 ») when a day was missed. */
export function Flame({
  streak,
  bare = false,
  className,
}: {
  streak: number;
  /** The icon only: the number is already written next to it. */
  bare?: boolean;
  className?: string;
}) {
  const t = useTranslations("games.streak");
  const alive = streak > 0;
  return (
    <span
      role="img"
      className={cn("inline-flex items-center gap-1 font-bold", className)}
      aria-label={t("aria", { count: streak })}
    >
      <Fire
        aria-hidden
        size={24}
        weight={alive ? "fill" : "regular"}
        className={alive ? "text-hibiscus" : "text-prune-doux"}
      />
      {!bare && <span aria-hidden>{streak}</span>}
    </span>
  );
}

/** Level of a client (Glow, Star, Icône). */
export function LevelBadge({ level, className }: { level: GlowLevel; className?: string }) {
  const t = useTranslations("games.levels");
  return (
    <Badge tone={level} className={className}>
      {t(level)}
    </Badge>
  );
}

/** Level of a pro: nothing for a new one, then Confirmed and Top pro. */
export function ProLevelBadge({ level, className }: { level: ProLevel; className?: string }) {
  const t = useTranslations("games.proLevels");
  if (level === 0) return null;
  return (
    <Badge tone={level === 2 ? "top" : "confirmed"} className={className}>
      {t(level === 2 ? "top" : "confirmed")}
    </Badge>
  );
}

/** A bar of progress with its words (never the colour alone). */
export function Progress({ value, max, label }: { value: number; max: number; label: string }) {
  const percent = max > 0 ? Math.min(100, Math.round((value * 100) / max)) : 100;
  return (
    <div className="flex flex-col gap-1">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={Math.min(value, max)}
        className="bg-carte h-3 overflow-hidden rounded-full"
      >
        <div className="bg-hibiscus h-full rounded-full" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-small text-prune-doux">{label}</p>
    </div>
  );
}
