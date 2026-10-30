"use client";

import { Eye, HandPointing, Megaphone, RocketLaunch } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { buyBoost, getBoosts, type BoostDuration } from "@/lib/api/ads";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/money";

/** « Boost my showcase »: first in the search and the feed of her city, a day or a week. */
export function BoostScreen({ justPaid }: { justPaid: boolean }) {
  const t = useTranslations("ads.boost");
  const tStatus = useTranslations("ads.boost.status");
  const locale = useLocale();
  const toast = useToast();
  const query = useQuery({ queryKey: ["boosts"], queryFn: getBoosts });
  const [duration, setDuration] = useState<BoostDuration>("week");
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const page = query.data;
  if (!page) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const date = (iso: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
      new Date(iso),
    );
  const price = page.prices ? page.prices[duration] : 0;
  const money = (amount: number) => formatMoney(amount, page.prices?.currency ?? "XOF", locale);

  const buy = async () => {
    setBusy(true);
    try {
      const { checkout_url } = await buyBoost(duration);
      window.location.assign(checkout_url);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <p className="text-prune-doux">{t("help")}</p>

      {page.running_until ? (
        <section className="bg-poudre rounded-card flex flex-col items-center gap-3 p-5 text-center">
          {justPaid && <Bloom label={t("running", { until: date(page.running_until) })} />}
          <RocketLaunch aria-hidden size={36} weight="duotone" className="text-hibiscus" />
          <p className="text-lead font-bold">{t("running", { until: date(page.running_until) })}</p>
        </section>
      ) : !page.open || !page.prices ? (
        <p className="font-bold">{t("closed")}</p>
      ) : (
        <section aria-labelledby="boost-choice" className="flex flex-col gap-3">
          <h2 id="boost-choice" className="text-title font-bold">
            {t("choose")}
          </h2>
          <div role="radiogroup" aria-labelledby="boost-choice" className="grid grid-cols-2 gap-3">
            {(["day", "week"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={duration === value}
                onClick={() => setDuration(value)}
                className={cn(
                  "rounded-card flex min-h-24 flex-col items-start justify-center gap-1 border-2 p-4 text-left",
                  duration === value ? "border-hibiscus bg-poudre" : "border-trait bg-carte",
                )}
              >
                <span className="font-bold">{t(value)}</span>
                <span className="text-lead font-bold">{money(page.prices![value])}</span>
              </button>
            ))}
          </div>
          <ul className="text-small text-prune-doux flex flex-col gap-1">
            <li>{t("where")}</li>
            <li>{t("sponsored")}</li>
            <li>{t("paidNow")}</li>
          </ul>
          <Button size="lg" fullWidth onClick={buy} disabled={busy || !price}>
            <Megaphone aria-hidden size={24} weight="bold" />
            {t("pay", { amount: money(price) })}
          </Button>
        </section>
      )}

      {page.boosts.length > 0 && (
        <section aria-labelledby="boost-history" className="flex flex-col gap-3">
          <h2 id="boost-history" className="text-title font-bold">
            {t("history")}
          </h2>
          <ul className="flex flex-col gap-2">
            {page.boosts.map((boost) => (
              <li
                key={boost.id}
                className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-4"
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="font-bold">{t(boost.duration)}</span>
                  <span className="text-small font-bold">{tStatus(boost.status)}</span>
                </span>
                {boost.starts_at && (
                  <span className="text-small text-prune-doux">
                    {t("from", { date: date(boost.starts_at) })}
                  </span>
                )}
                <span className="flex gap-4">
                  <span className="inline-flex items-center gap-1">
                    <Eye aria-hidden size={20} />
                    {t("impressions", { count: boost.impressions })}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <HandPointing aria-hidden size={20} />
                    {t("clicks", { count: boost.clicks })}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
