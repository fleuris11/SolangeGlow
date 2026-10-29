"use client";

import { CaretRight } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { getGlowMe } from "@/lib/api/games";
import { Link } from "@/lib/i18n/navigation";

import { Flame, LevelBadge } from "./glow-bits";

/** On « Me »: the flame of the streak, the points and the level, opening « My points ». */
export function GlowStatus() {
  const t = useTranslations("games.status");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["glow-me"], queryFn: getGlowMe, retry: false });
  const glow = query.data;
  if (!glow || !glow.games_open) return null;
  return (
    <Link
      href="/points"
      className="bg-poudre rounded-card flex min-h-16 items-center gap-4 p-4"
      aria-label={t("aria", {
        points: glow.balance,
        days: glow.streak.streak,
      })}
    >
      <Flame streak={glow.streak.streak} className="text-title" />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="font-bold">
          {t("points", { points: new Intl.NumberFormat(locale).format(glow.balance) })}
        </span>
        <span className="text-small text-prune-doux">{t("open")}</span>
      </span>
      <LevelBadge level={glow.level} />
      <CaretRight aria-hidden size={20} />
    </Link>
  );
}
