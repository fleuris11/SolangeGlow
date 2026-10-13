"use client";

import { CheckCircle, Key } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { courierConfirm, getCourierPayment } from "@/lib/api/payments";

/** The courier, without account, types the client's code at the handover. */
export function CourierConfirm({ token }: { token: string }) {
  const t = useTranslations("payments.courier");
  const [code, setCode] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const query = useQuery({
    queryKey: ["courier", token],
    queryFn: () => getCourierPayment(token),
    retry: false,
  });

  if (query.isPending) return <Skeleton className="rounded-card h-60" />;
  if (query.isError) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  if (done) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center" role="status">
        <CheckCircle aria-hidden size={64} weight="fill" className="text-feuille" />
        <h1 className="text-headline font-bold">{t("doneTitle")}</h1>
        <p>{t("doneText")}</p>
      </div>
    );
  }
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        setError(undefined);
        courierConfirm(token, code)
          .then(() => setDone(true))
          .catch((failure: unknown) =>
            setError(failure instanceof ApiError ? failure.message : t("error")),
          )
          .finally(() => setBusy(false));
      }}
    >
      <h1 className="text-headline flex items-center gap-2 font-bold">
        <Key aria-hidden size={28} weight="bold" />
        {t("title")}
      </h1>
      <p>{t("order", { reference: query.data.reference, seller: query.data.seller })}</p>
      <p className="font-bold">{query.data.description}</p>
      <p className="text-small text-prune-doux">{t("help")}</p>
      <Input
        label={t("code")}
        inputMode="numeric"
        maxLength={6}
        value={code}
        error={error}
        onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
      />
      <Button type="submit" size="lg" disabled={busy || code.length !== 6}>
        {t("confirm")}
      </Button>
    </form>
  );
}
