"use client";

import { CheckCircle, Ticket } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { cancelPass, getPass, subscribePass } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

/** The monthly pass: what it opens, its price, paid month by month (never taken by itself). */
export function PassScreen() {
  const t = useTranslations("academy.pass");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["academy-pass"], queryFn: getPass });
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="h-64 rounded-2xl" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const pass = query.data;
  const price =
    pass.price_minor !== null && pass.price_minor !== undefined
      ? formatMoney(pass.price_minor, pass.currency, locale)
      : null;
  const until = pass.current_period_end
    ? new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
        new Date(pass.current_period_end),
      )
    : null;

  const run = async (action: () => Promise<unknown>, message?: string) => {
    setBusy(true);
    try {
      const answer = (await action()) as { checkout_url?: string } | undefined;
      if (answer?.checkout_url) {
        window.location.assign(answer.checkout_url);
        return;
      }
      if (message) toast(message, "success");
      await queryClient.invalidateQueries({ queryKey: ["academy-pass"] });
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Ticket aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={`${t("title")}. ${t("intro")}`} />
      </div>
      <p className="text-lead">{t("intro")}</p>
      <ul className="flex flex-col gap-2">
        {(["point1", "point2", "point3"] as const).map((key) => (
          <li key={key} className="flex items-start gap-2">
            <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille shrink-0" />
            {t(key)}
          </li>
        ))}
      </ul>

      {price === null ? (
        <p className="bg-poudre rounded-2xl p-3 font-bold">{t("notOffered")}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {pass.active ? (
            <p className="bg-poudre rounded-2xl p-3 font-bold">
              {pass.cancel_at_period_end
                ? t("stopsOn", { date: until ?? "" })
                : t("activeUntil", { date: until ?? "" })}
            </p>
          ) : (
            <p className="text-title font-bold">{t("price", { price })}</p>
          )}
          {(!pass.active || pass.payment_due) && (
            <Button size="lg" fullWidth disabled={busy} onClick={() => void run(subscribePass)}>
              <Ticket aria-hidden size={24} weight="bold" />
              {pass.active ? t("payNext", { price }) : t("take", { price })}
            </Button>
          )}
          {pass.active && !pass.cancel_at_period_end && (
            <Button
              variant="quiet"
              fullWidth
              disabled={busy}
              onClick={() => void run(cancelPass, t("stopped"))}
            >
              {t("stop")}
            </Button>
          )}
          <p className="text-small text-prune-doux">{t("noAuto")}</p>
        </div>
      )}
      <Link
        href="/academie?pricing=pass"
        className={buttonClasses({ variant: "secondary", fullWidth: true })}
      >
        {t("courses")}
      </Link>
    </div>
  );
}
