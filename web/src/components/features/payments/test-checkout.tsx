"use client";

import { CheckCircle, Flask, Prohibit, XCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getPayment, testOutcome } from "@/lib/api/payments";
import { useRouter } from "@/lib/i18n/navigation";

import { Breakdown } from "./payment-parts";

/** The test provider's payment page: choose what the « bank » answers. */
export function TestCheckout({ paymentId }: { paymentId: string }) {
  const t = useTranslations("payments.test");
  const toast = useToast();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const query = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => getPayment(paymentId),
  });

  const answer = async (outcome: "succeeded" | "failed" | "abandoned") => {
    setBusy(true);
    try {
      await testOutcome(paymentId, outcome);
      const paid = query.data;
      // A gift from abroad goes back to its follow-up (« Paid, it will leave… »).
      router.push(
        paid?.source_type === "gift" && paid.source_id
          ? `/cadeaux/${paid.source_id}?paid=1`
          : `/payments/${paymentId}`,
      );
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
  return (
    <div className="flex flex-col gap-6">
      <div className="bg-or text-sur-or rounded-card flex gap-3 p-4">
        <Flask aria-hidden size={28} weight="fill" className="shrink-0" />
        <p className="font-bold">{t("banner")}</p>
      </div>
      <h1 className="text-headline font-bold">{t("title")}</h1>
      <p>{query.data.description}</p>
      <Breakdown payment={query.data} />
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
