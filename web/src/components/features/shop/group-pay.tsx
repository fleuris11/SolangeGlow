"use client";

import { CheckCircle, Flask, Prohibit, XCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getPaymentGroup, testGroupOutcome } from "@/lib/api/shop";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { CART_KEY } from "./cart";

/** The test provider's page for a whole cart: choose what the « bank » answers. */
export function TestGroupCheckout({ groupId }: { groupId: string }) {
  const t = useTranslations("payments.test");
  const tShop = useTranslations("shop.done");
  const locale = useLocale();
  const toast = useToast();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const query = useQuery({ queryKey: ["group", groupId], queryFn: () => getPaymentGroup(groupId) });

  const answer = async (outcome: "succeeded" | "failed" | "abandoned") => {
    setBusy(true);
    try {
      await testGroupOutcome(groupId, outcome);
      router.push(`/checkout/done/${groupId}`);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
      setBusy(false);
    }
  };

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {t("error")}
      </p>
    );
  }
  const group = query.data;
  return (
    <div className="flex flex-col gap-6">
      <div className="bg-or text-sur-or rounded-card flex gap-3 p-4">
        <Flask aria-hidden size={28} weight="fill" className="shrink-0" />
        <p className="font-bold">{t("banner")}</p>
      </div>
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <ul className="flex flex-col gap-2">
        {group.payments.map((payment) => (
          <li key={payment.id} className="flex justify-between gap-4">
            <span>{payment.description}</span>
            <span className="font-bold whitespace-nowrap">
              {formatMoney(payment.total_minor, payment.currency, locale)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-title flex justify-between font-bold">
        <span>{tShop("total")}</span>
        <span>{formatMoney(group.total_minor, group.currency, locale)}</span>
      </p>
      <div className="flex flex-col gap-3">
        <Button size="lg" fullWidth disabled={busy} onClick={() => void answer("succeeded")}>
          <CheckCircle aria-hidden size={24} weight="bold" />
          {t("succeeded")}
        </Button>
        <Button variant="secondary" fullWidth disabled={busy} onClick={() => void answer("failed")}>
          <XCircle aria-hidden size={24} weight="bold" />
          {t("failed")}
        </Button>
        <Button variant="quiet" fullWidth disabled={busy} onClick={() => void answer("abandoned")}>
          <Prohibit aria-hidden size={24} weight="bold" />
          {t("abandoned")}
        </Button>
      </div>
    </div>
  );
}

/** Back from the payment page: waits for the provider, then shows the orders. */
export function CheckoutDone({ groupId }: { groupId: string }) {
  const t = useTranslations("shop.done");
  const locale = useLocale();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["group", groupId],
    queryFn: () => getPaymentGroup(groupId),
    refetchInterval: (q) => (q.state.data?.status === "pending" ? 3000 : false),
  });
  const status = query.data?.status;
  useEffect(() => {
    // The cart was emptied on the server: show it as it is now.
    if (status === "paid") void queryClient.invalidateQueries({ queryKey: CART_KEY });
  }, [status, queryClient]);

  if (query.isPending) return <Skeleton className="rounded-card h-80" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {t("error")}
      </p>
    );
  }
  const group = query.data;
  if (group.status === "pending") {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center" role="status">
        <Skeleton className="size-24 rounded-full" />
        <h1 className="text-headline font-bold">{t("waiting")}</h1>
        <p className="text-prune-doux">{t("waitingHelp")}</p>
        {group.checkout_url && (
          <a href={group.checkout_url} className={buttonClasses({ variant: "secondary" })}>
            {t("payAgain")}
          </a>
        )}
      </div>
    );
  }
  if (group.status === "cancelled") {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <h1 className="text-headline font-bold">{t("cancelled")}</h1>
        <p className="text-prune-doux">{t("cancelledHelp")}</p>
        <Link href="/cart" className={buttonClasses({ size: "lg" })}>
          {t("backToCart")}
        </Link>
      </div>
    );
  }
  const orders = group.payments.filter((p) => p.source_type === "order" && p.source_id);
  return (
    <section aria-labelledby="done" className="flex flex-col items-center gap-5 py-6 text-center">
      <Bloom label={t("paid")} size={140} />
      <h1 id="done" className="font-display text-display font-black">
        {t("paid")}
      </h1>
      <p className="text-lead max-w-[34ch]">
        {t("paidHelp", { amount: formatMoney(group.total_minor, group.currency, locale) })}
      </p>
      <SpeakButton text={`${t("paid")}. ${t("codeHelp")}`} />
      <p className="bg-poudre rounded-2xl p-4">{t("codeHelp")}</p>
      <ul className="flex w-full flex-col gap-2">
        {orders.map((payment) => (
          <li key={payment.id}>
            <Link
              href={`/orders/${payment.source_id}`}
              className={buttonClasses({ variant: "secondary", fullWidth: true })}
            >
              {t("seeOrder", { shop: payment.seller.name })}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
