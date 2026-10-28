"use client";

import { Broadcast, CalendarPlus, Play, X } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { PriceTag } from "@/components/ui/price-tag";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { cancelSaleLive, getMySaleLives, planSaleLive, type MySaleLives } from "@/lib/api/live";
import { Link } from "@/lib/i18n/navigation";

const LENGTHS = [30, 45, 60, 90];
const KEY = ["my-sale-lives"];

/** « My lives » of the shop: plan one, open its room, see what it sold. */
export function MySaleLivesTab() {
  const t = useTranslations("live.mine");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: KEY, queryFn: getMySaleLives });
  const [title, setTitle] = useState("");
  const [when, setWhen] = useState("");
  const [length, setLength] = useState(45);
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="h-40 rounded-2xl" />;
  if (query.isError || !query.data) {
    return <p className="font-bold">{t("error")}</p>;
  }
  const data = query.data;
  const set = (value: MySaleLives) => queryClient.setQueryData(KEY, value);
  const full = data.quota.used >= data.quota.allowed;

  const plan = async () => {
    setBusy(true);
    try {
      set(
        await planSaleLive({
          title: title.trim(),
          starts_at: new Date(when).toISOString(),
          duration_minutes: length,
        }),
      );
      setTitle("");
      setWhen("");
      toast(t("planned"), "success");
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  if (!data.open) return <p className="bg-poudre rounded-2xl p-3">{t("closed")}</p>;

  return (
    <div className="flex flex-col gap-6">
      <p className="text-prune-doux">
        {t("quota", { used: data.quota.used, allowed: data.quota.allowed })}
      </p>
      {data.can_sell ? (
        <form
          className="border-trait rounded-card flex flex-col gap-4 border p-4"
          onSubmit={(event) => {
            event.preventDefault();
            void plan();
          }}
        >
          <h2 className="text-lead font-bold">{t("new")}</h2>
          <Input
            label={t("title")}
            value={title}
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
          />
          <Input
            label={t("when")}
            type="datetime-local"
            value={when}
            onChange={(event) => setWhen(event.target.value)}
            required
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("length")}</legend>
            <div className="flex flex-wrap gap-2">
              {LENGTHS.map((minutes) => (
                <button
                  key={minutes}
                  type="button"
                  aria-pressed={length === minutes}
                  onClick={() => setLength(minutes)}
                  className={
                    length === minutes
                      ? "border-hibiscus bg-poudre min-h-12 rounded-full border-2 px-4 font-bold"
                      : "border-trait min-h-12 rounded-full border-2 px-4 font-bold"
                  }
                >
                  {t("minutes", { minutes })}
                </button>
              ))}
            </div>
          </fieldset>
          <Button type="submit" size="lg" disabled={busy || full || !title.trim() || !when}>
            <CalendarPlus aria-hidden size={24} weight="bold" />
            {t("plan")}
          </Button>
          {full && (
            <p className="text-small">
              {t("full")}{" "}
              <Link href="/pro/plan" className="font-bold underline">
                {t("premium")}
              </Link>
            </p>
          )}
        </form>
      ) : (
        <p className="bg-poudre rounded-2xl p-3 font-bold">{t("verify")}</p>
      )}

      {data.results.length === 0 ? (
        <EmptyState
          icon={<Broadcast size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {data.results.map((live) => (
            <li key={live.id} className="border-trait rounded-card flex flex-col gap-3 border p-4">
              <div className="flex flex-col gap-1">
                <p className="font-bold">{live.title}</p>
                <p className="text-small text-prune-doux">
                  {new Intl.DateTimeFormat(locale, {
                    dateStyle: "full",
                    timeStyle: "short",
                    timeZone: live.time_zone,
                  }).format(new Date(live.starts_at))}
                </p>
                <p className="text-small font-bold">{t(`status.${live.status}`)}</p>
              </div>
              {live.status === "ended" && (
                <dl className="grid grid-cols-2 gap-2">
                  <div className="bg-poudre rounded-2xl p-3">
                    <dt className="text-small">{t("viewers")}</dt>
                    <dd className="text-title font-bold">{live.total_viewers}</dd>
                  </div>
                  <div className="bg-poudre rounded-2xl p-3">
                    <dt className="text-small">{t("orders")}</dt>
                    <dd className="text-title font-bold">{live.orders_count}</dd>
                  </div>
                  <div className="bg-poudre col-span-2 rounded-2xl p-3">
                    <dt className="text-small">{t("sales")}</dt>
                    <dd className="text-title">
                      <PriceTag amountMinor={live.revenue_minor} currency={live.currency} />
                    </dd>
                  </div>
                </dl>
              )}
              <div className="flex flex-wrap gap-2">
                <Link href={live.link} className={buttonClasses({})}>
                  {live.status === "ended" ? (
                    <Play aria-hidden size={20} weight="fill" />
                  ) : (
                    <Broadcast aria-hidden size={20} weight="bold" />
                  )}
                  {live.status === "ended" ? t("seeReplay") : t("openRoom")}
                </Link>
                {live.status === "scheduled" && (
                  <Button
                    variant="quiet"
                    disabled={busy}
                    onClick={() =>
                      void cancelSaleLive(live.id)
                        .then(set)
                        .catch((error: unknown) =>
                          toast(error instanceof ApiError ? error.message : t("error"), "warning"),
                        )
                    }
                  >
                    <X aria-hidden size={20} weight="bold" />
                    {t("cancel")}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
