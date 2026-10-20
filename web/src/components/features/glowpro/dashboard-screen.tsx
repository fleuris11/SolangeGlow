"use client";

import { ArrowDown, ArrowUp, ChartBar } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { getDashboard, type PeriodStats } from "@/lib/api/glowpro";
import { addDays } from "@/lib/booking/time";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/money";

import { PremiumOffer } from "./premium-gate";

type Period = "month" | "last_month" | "quarter";

function periodOf(period: Period, today: string): { start: string; end: string } {
  const [y, m] = today.split("-").map(Number) as [number, number];
  const first = (year: number, month: number) => `${year}-${String(month).padStart(2, "0")}-01`;
  if (period === "month") return { start: first(y, m), end: today };
  if (period === "last_month") {
    const [py, pm] = m === 1 ? [y - 1, 12] : [y, m - 1];
    return { start: first(py, pm), end: addDays(first(y, m), -1) };
  }
  return { start: addDays(today, -89), end: today };
}

function Trend({ now, before }: { now: number; before?: number }) {
  const t = useTranslations("glowpro.dashboard");
  if (before === undefined) return null;
  const diff = before ? Math.round(((now - before) / before) * 100) : now ? 100 : 0;
  const up = diff >= 0;
  return (
    <span
      className={cn(
        "text-small flex items-center gap-1 font-bold",
        up ? "text-feuille" : "text-alerte",
      )}
    >
      {up ? (
        <ArrowUp aria-hidden size={16} weight="bold" />
      ) : (
        <ArrowDown aria-hidden size={16} weight="bold" />
      )}
      {t("vsBefore", { diff: `${up ? "+" : ""}${diff}` })}
    </span>
  );
}

function Tile({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="border-trait bg-carte rounded-card flex min-w-0 flex-col gap-1 border p-3">
      <span className="text-small text-prune-doux">{label}</span>
      <span className="text-lead font-bold break-words">{value}</span>
      {children}
    </div>
  );
}

/** Bars of the turnover, day by day (or week by week); every value is also written. */
function SeriesChart({ stats, currency }: { stats: PeriodStats; currency: string }) {
  const t = useTranslations("glowpro.dashboard");
  const locale = useLocale();
  const max = Math.max(1, ...stats.series.map((p) => p.turnover_minor));
  const width = 320;
  const height = 120;
  const bar = width / Math.max(1, stats.series.length);
  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="font-bold">{t("chartTitle")}</figcaption>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-32 w-full"
        role="img"
        aria-label={t("chartTitle")}
      >
        {stats.series.map((point, i) => {
          const h = Math.round((point.turnover_minor / max) * (height - 4));
          return (
            <rect
              key={point.day}
              x={i * bar + 1}
              y={height - h}
              width={Math.max(1, bar - 2)}
              height={h}
              rx={Math.min(3, bar / 3)}
              className="fill-hibiscus"
            />
          );
        })}
        <line x1="0" x2={width} y1={height - 0.5} y2={height - 0.5} className="stroke-trait" />
      </svg>
      <details>
        <summary className="text-small min-h-12 cursor-pointer py-3 font-bold">
          {t("asTable")}
        </summary>
        <table className="text-small w-full">
          <thead>
            <tr>
              <th scope="col" className="text-left">
                {t("day")}
              </th>
              <th scope="col" className="text-right">
                {t("turnover")}
              </th>
            </tr>
          </thead>
          <tbody>
            {stats.series.map((point) => (
              <tr key={point.day}>
                <td>
                  {new Intl.DateTimeFormat(locale, {
                    day: "numeric",
                    month: "short",
                    timeZone: "UTC",
                  }).format(new Date(`${point.day}T12:00:00Z`))}
                </td>
                <td className="text-right">
                  {formatMoney(point.turnover_minor, currency, locale)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

function Ranking({
  title,
  rows,
  currency,
}: {
  title: string;
  rows: {
    id: string;
    name: string;
    appointments: number;
    turnover_minor: number;
    occupancy?: number;
    color?: string;
  }[];
  currency: string;
}) {
  const t = useTranslations("glowpro.dashboard");
  const locale = useLocale();
  const max = Math.max(1, ...rows.map((r) => r.turnover_minor));
  if (!rows.length) return null;
  return (
    <section className="flex flex-col gap-3" aria-label={title}>
      <h2 className="text-lead font-bold">{title}</h2>
      <ul className="flex flex-col gap-3">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-bold">{row.name}</span>
              <span className="text-small">
                {formatMoney(row.turnover_minor, currency, locale)}
              </span>
            </div>
            <div className="bg-poudre h-3 overflow-hidden rounded-full" aria-hidden>
              <div
                className="bg-hibiscus h-full rounded-full"
                style={{
                  width: `${Math.round((row.turnover_minor / max) * 100)}%`,
                  backgroundColor: row.color,
                }}
              />
            </div>
            <span className="text-small text-prune-doux">
              {t("appointments", { count: row.appointments })}
              {row.occupancy !== undefined && `, ${t("occupancyShort", { rate: row.occupancy })}`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** « Dashboard »: free = the month in two numbers; Premium = everything, with the period before. */
export function DashboardScreen() {
  const t = useTranslations("glowpro.dashboard");
  const locale = useLocale();
  const [period, setPeriod] = useState<Period>("month");
  const today = new Date().toISOString().slice(0, 10);
  const range = periodOf(period, today);
  const query = useQuery({
    queryKey: ["dashboard", range.start, range.end],
    queryFn: () => getDashboard(range),
  });

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  if (!query.data) return <p className="text-prune-doux">{t("error")}</p>;
  const data = query.data;
  const currency = data.currency;
  const money = (value: number) => formatMoney(value, currency, locale);
  const current = data.current;
  const previous = data.previous ?? undefined;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <ChartBar aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton
          text={
            current
              ? t("spoken", {
                  turnover: money(current.turnover_minor),
                  count: current.appointments,
                  rate: current.occupancy,
                })
              : t("spokenBasic", {
                  turnover: money(data.basic.turnover_minor),
                  count: data.basic.appointments,
                })
          }
        />
      </div>

      {data.level === "basic" || !current ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Tile label={t("turnoverMonth")} value={money(data.basic.turnover_minor)} />
            <Tile label={t("appointmentsMonth")} value={String(data.basic.appointments)} />
          </div>
          <PremiumOffer title={t("premiumTitle")} text={t("premiumText")} />
        </>
      ) : (
        <>
          <div
            role="tablist"
            aria-label={t("period")}
            className="bg-poudre grid grid-cols-3 rounded-full p-1"
          >
            {(["month", "last_month", "quarter"] as const).map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={period === key}
                onClick={() => setPeriod(key)}
                className={cn(
                  "text-small min-h-12 rounded-full px-2 font-bold",
                  period === key ? "bg-carte text-prune" : "text-prune-doux",
                )}
              >
                {t(`periods.${key}`)}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Tile label={t("turnover")} value={money(current.turnover_minor)}>
              <Trend now={current.turnover_minor} before={previous?.turnover_minor} />
            </Tile>
            <Tile label={t("collected")} value={money(current.collected_minor)} />
            <Tile label={t("occupancy")} value={`${current.occupancy} %`}>
              <Trend now={current.occupancy} before={previous?.occupancy} />
            </Tile>
            <Tile label={t("average")} value={money(current.average_minor)} />
            <Tile label={t("appointmentsDone")} value={String(current.appointments)}>
              <Trend now={current.appointments} before={previous?.appointments} />
            </Tile>
            <Tile label={t("clients")} value={String(current.clients)}>
              <span className="text-small text-prune-doux">
                {t("newAndLoyal", { new: current.new_clients, loyal: current.loyal_clients })}
              </span>
            </Tile>
          </div>
          <SeriesChart stats={current} currency={currency} />
          <Ranking title={t("byPerson")} rows={current.staff} currency={currency} />
          <Ranking title={t("byService")} rows={current.services} currency={currency} />
        </>
      )}
    </div>
  );
}
