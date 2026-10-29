"use client";

import { CalendarStar, Gift, MagnifyingGlass, Medal, Star, Trophy } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { buttonClasses } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { getCelebrations, getRankings } from "@/lib/api/games";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { ProLevelBadge } from "./glow-bits";

/** The calendar of celebrations: the next big days, with the pros of the moment. */
export function CalendarScreen() {
  const t = useTranslations("games.calendar");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["glow-celebrations"], queryFn: getCelebrations });
  const date = (iso: string) =>
    new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(
      new Date(`${iso}T12:00:00`),
    );
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <p className="text-prune-doux">{t("help")}</p>
      {query.isPending && <Skeleton className="rounded-card h-80" />}
      {query.data?.length === 0 && (
        <EmptyState icon={<CalendarStar size={48} weight="duotone" />} title={t("none")} />
      )}
      <ul className="flex flex-col gap-3">
        {query.data?.map((day) => (
          <li
            key={day.id}
            className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
          >
            <div className="flex items-start gap-3">
              <CalendarStar
                aria-hidden
                size={32}
                weight="duotone"
                className="text-hibiscus shrink-0"
              />
              <div className="flex min-w-0 flex-1 flex-col">
                <h2 className="text-lead font-bold">{day.name}</h2>
                <span className="text-small">{date(day.date)}</span>
                <span className="text-small text-prune-doux font-bold">
                  {day.days_left === 0 ? t("today") : t("inDays", { count: day.days_left })}
                </span>
              </div>
            </div>
            {day.message && <p>{day.message}</p>}
            <div className="flex flex-col gap-2">
              {day.trade && (
                <Link
                  href={`/explore?trade=${day.trade}`}
                  className={buttonClasses({ variant: "secondary", fullWidth: true })}
                >
                  <MagnifyingGlass aria-hidden size={20} weight="bold" />
                  {t("findPro")}
                </Link>
              )}
              {day.gift_occasion && (
                <Link
                  href="/offrir"
                  className={buttonClasses({ variant: "quiet", fullWidth: true })}
                >
                  <Gift aria-hidden size={20} weight="bold" />
                  {t("offer")}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

const PODIUM = [
  <Trophy key="1" aria-hidden size={28} weight="fill" className="text-or" />,
  <Medal key="2" aria-hidden size={28} weight="fill" className="text-prune-doux" />,
  <Medal key="3" aria-hidden size={28} weight="duotone" className="text-or" />,
];

/** Top pros of the month per city and trade, on the verified reviews. */
export function RankingsScreen() {
  const t = useTranslations("games.rankings");
  const locale = useLocale();
  const [city, setCity] = useState<string | undefined>();
  const [trade, setTrade] = useState<string | undefined>();
  const query = useQuery({
    queryKey: ["glow-rankings", city, trade],
    queryFn: () => getRankings({ city, trade }),
  });
  const data = query.data;
  const month = data?.month
    ? new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(
        new Date(`${data.month}T12:00:00`),
      )
    : "";
  const number = (value: string) =>
    new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(Number(value));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <p className="text-prune-doux">{t("help")}</p>
      {query.isPending && <Skeleton className="rounded-card h-80" />}
      {data && !data.month && (
        <EmptyState icon={<Trophy size={48} weight="duotone" />} title={t("none")} />
      )}
      {data?.month && (
        <>
          <p className="text-lead font-bold">{t("month", { month })}</p>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 font-bold">{t("city")}</legend>
            <div className="flex flex-wrap gap-2">
              {data.cities.map((value) => (
                <Chip key={value} selected={data.city === value} onClick={() => setCity(value)}>
                  {value}
                </Chip>
              ))}
            </div>
          </fieldset>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 font-bold">{t("trade")}</legend>
            <div className="flex flex-wrap gap-2">
              {data.trades.map((value) => (
                <Chip
                  key={value.key}
                  selected={data.trade === value.key}
                  onClick={() => setTrade(value.key)}
                >
                  {value.name}
                </Chip>
              ))}
            </div>
          </fieldset>
          {data.rows.length === 0 ? (
            <p className="text-prune-doux">{t("empty")}</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {data.rows.map((row) => (
                <li key={row.slug}>
                  <Link
                    href={`/${row.slug}`}
                    className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
                  >
                    <span className="flex w-8 shrink-0 justify-center font-bold">
                      {row.position <= 3 ? PODIUM[row.position - 1] : row.position}
                      <span className="sr-only">{t("position", { position: row.position })}</span>
                    </span>
                    <Avatar name={row.name} src={mediaSrc(row.photo, "thumb")} size="sm" />
                    <span className="flex min-w-0 flex-1 flex-col gap-1">
                      <span className="truncate font-bold">{row.name}</span>
                      <span className="text-small inline-flex items-center gap-1">
                        <Star aria-hidden size={16} weight="fill" className="text-or" />
                        {t("rating", { average: number(row.average), count: row.reviews })}
                      </span>
                      <ProLevelBadge level={row.level} className="self-start" />
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}
