"use client";

import { Check, Crown, FilePdf, Sparkle, X } from "@phosphor-icons/react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  cancelPlan,
  resumePlan,
  startTrial,
  subscribe,
  type GlowFeature,
  type GlowPlan,
} from "@/lib/api/glowpro";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/money";

import { useGlowPro } from "./premium-gate";

const FEATURES: GlowFeature[] = [
  "extra_staff",
  "client_file",
  "stock",
  "dashboard_full",
  "campaigns",
  "widget",
  "einvoice",
];

function day(value: string | null | undefined, locale: string) {
  if (!value) return "";
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric" }).format(
    new Date(value),
  );
}

/** « My plan »: free or Premium, trial, the month to pay, the invoices. */
export function PlanScreen() {
  const t = useTranslations("glowpro.plan");
  const tFeature = useTranslations("glowpro.features");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data, isPending, isError } = useGlowPro();
  const [busy, setBusy] = useState(false);

  if (isPending) return <Skeleton className="rounded-card h-96" />;
  if (isError || !data) return <p className="text-prune-doux">{t("notPro")}</p>;

  const sub = data.subscription;
  const premium = data.plans.find((p) => !p.is_default) as GlowPlan | undefined;
  const onPremium = !data.current.is_default;
  const status = onPremium
    ? sub.status === "trialing"
      ? t("trialUntil", { date: day(sub.current_period_end, locale) })
      : sub.status === "past_due"
        ? t("pastDue", { date: day(sub.grace_until, locale) })
        : sub.cancel_at_period_end
          ? t("endsOn", { date: day(sub.current_period_end, locale) })
          : t("paidUntil", { date: day(sub.current_period_end, locale) })
    : t("onFree");

  const run = async (action: () => Promise<{ checkout_url?: string } | unknown>, done?: string) => {
    setBusy(true);
    try {
      const answer = await action();
      const url = (answer as { checkout_url?: string } | undefined)?.checkout_url;
      if (url) {
        window.location.assign(url);
        return;
      }
      await queryClient.invalidateQueries();
      if (done) toast(done, "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const price = premium?.price_minor
    ? t("perMonth", { price: formatMoney(premium.price_minor, premium.currency, locale) })
    : "";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${data.current.name}. ${status}`} />
      </div>

      <section
        aria-labelledby="current"
        className={cn(
          "rounded-card flex flex-col gap-2 p-5",
          onPremium ? "bg-poudre" : "border-trait border",
        )}
      >
        <h2 id="current" className="text-title flex items-center gap-2 font-bold">
          {onPremium && <Crown aria-hidden size={26} weight="duotone" className="text-hibiscus" />}
          {data.current.name}
        </h2>
        <p className="font-bold">{status}</p>
        {data.usage.staff_limit !== null && (
          <p className="text-prune-doux">
            {t("team", { count: data.usage.staff, limit: data.usage.staff_limit })}
          </p>
        )}
      </section>

      {premium && (
        <section aria-labelledby="compare" className="flex flex-col gap-3">
          <h2 id="compare" className="text-title font-bold">
            {t("compare")}
          </h2>
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">{t("compare")}</caption>
            <thead>
              <tr className="border-trait border-b">
                <th scope="col" className="py-2 font-bold">
                  {t("what")}
                </th>
                <th scope="col" className="w-20 py-2 text-center font-bold">
                  {t("free")}
                </th>
                <th scope="col" className="w-24 py-2 text-center font-bold">
                  {premium.name}
                </th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((feature) => (
                <tr key={feature} className="border-trait border-b">
                  <th scope="row" className="py-3 font-normal">
                    {tFeature(feature)}
                  </th>
                  <td className="text-center">
                    <X aria-label={t("no")} size={22} className="text-prune-doux inline" />
                  </td>
                  <td className="text-center">
                    <Check
                      aria-label={t("yes")}
                      size={22}
                      weight="bold"
                      className="text-feuille inline"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {price && <p className="text-lead font-bold">{price}</p>}
          <p className="text-small text-prune-doux">{t("noCommitment")}</p>

          {!onPremium && !sub.trial_used && premium.trial_days > 0 && (
            <Button
              size="lg"
              fullWidth
              disabled={busy}
              onClick={() => void run(startTrial, t("trialStarted"))}
            >
              <Sparkle aria-hidden size={24} weight="bold" />
              {t("try", { days: premium.trial_days })}
            </Button>
          )}
          {(!onPremium || sub.status !== "active" || sub.payment_due || sub.cancel_at_period_end) &&
            (sub.trial_used || onPremium) && (
              <Button
                size="lg"
                fullWidth
                variant={onPremium && sub.status === "trialing" ? "secondary" : "primary"}
                disabled={busy}
                onClick={() => void run(subscribe)}
              >
                {t("pay")}
              </Button>
            )}
          {onPremium && !sub.cancel_at_period_end && (
            <Button
              variant="quiet"
              fullWidth
              disabled={busy}
              onClick={() => void run(cancelPlan, t("cancelled"))}
            >
              {t("cancel")}
            </Button>
          )}
          {onPremium && sub.cancel_at_period_end && (
            <Button
              variant="secondary"
              fullWidth
              disabled={busy}
              onClick={() => void run(resumePlan, t("resumed"))}
            >
              {t("resume")}
            </Button>
          )}
          <p className="text-small text-prune-doux">{t("downgradeRule")}</p>
        </section>
      )}

      {data.invoices.length > 0 && (
        <section aria-labelledby="invoices" className="flex flex-col gap-2">
          <h2 id="invoices" className="text-title font-bold">
            {t("invoices")}
          </h2>
          <ul className="flex flex-col gap-2">
            {data.invoices.map((invoice) => (
              <li key={invoice.id}>
                <a
                  href={invoice.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="border-trait hover:bg-poudre rounded-card flex min-h-12 items-center gap-3 border p-3"
                >
                  <FilePdf aria-hidden size={24} className="text-hibiscus" />
                  <span className="flex-1 font-bold">{invoice.number}</span>
                  <span>{formatMoney(invoice.total_minor, invoice.currency, locale)}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
