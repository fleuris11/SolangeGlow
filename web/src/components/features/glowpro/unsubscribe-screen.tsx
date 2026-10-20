"use client";

import { BellSlash, CheckCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { getUnsubscribe, unsubscribe } from "@/lib/api/glowpro";

/** The link at the bottom of a salon's message: one tap to stop receiving its offers. */
export function UnsubscribeScreen({ token }: { token: string }) {
  const t = useTranslations("glowpro.unsubscribe");
  const query = useQuery({
    queryKey: ["unsubscribe", token],
    queryFn: () => getUnsubscribe(token),
    retry: false,
  });
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-60" />;
  if (!query.data) {
    return <EmptyState icon={<BellSlash size={44} weight="duotone" />} title={t("broken")} />;
  }
  const info = query.data;
  if (done || info.unsubscribed) {
    return (
      <EmptyState
        icon={<CheckCircle size={44} weight="fill" className="text-feuille" />}
        title={t("done", { name: info.pro_name })}
        description={t("doneHelp")}
      />
    );
  }
  return (
    <div className="flex flex-col items-center gap-5 text-center">
      <BellSlash aria-hidden size={48} weight="duotone" className="text-hibiscus" />
      <h1 className="text-headline font-bold">{t("title", { name: info.pro_name })}</h1>
      <p className="text-prune-doux">{t(`help.${info.channel}`)}</p>
      <Button
        size="lg"
        fullWidth
        disabled={busy}
        onClick={() => {
          setBusy(true);
          void unsubscribe(token)
            .then(() => setDone(true))
            .finally(() => setBusy(false));
        }}
      >
        {t("confirm")}
      </Button>
    </div>
  );
}
