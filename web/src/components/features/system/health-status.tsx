"use client";

import { CheckCircle, CircleNotch, WarningCircle } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { getHealth, healthQueryKey } from "@/lib/api/health";

export function HealthStatus() {
  const t = useTranslations("health");
  const { data, isPending, isError, isFetching, refetch } = useQuery({
    queryKey: healthQueryKey,
    queryFn: getHealth,
    retry: false,
  });

  return (
    <section
      aria-labelledby="health-title"
      className="border-trait bg-carte w-full rounded-[20px] border p-6"
    >
      <h2 id="health-title" className="text-prune-doux text-[15px] leading-[22px]">
        {t("title")}
      </h2>

      <div role="status" aria-live="polite" className="mt-3 flex items-center gap-3">
        {isPending ? (
          <>
            <CircleNotch
              aria-hidden
              size={28}
              className="text-prune-doux animate-spin motion-reduce:animate-none"
            />
            <span>{t("checking")}</span>
          </>
        ) : isError || data?.status !== "ok" ? (
          <>
            <WarningCircle
              aria-hidden
              size={28}
              weight="duotone"
              className="text-alerte shrink-0"
            />
            <span>{t("error")}</span>
          </>
        ) : (
          <>
            <CheckCircle aria-hidden size={28} weight="duotone" className="text-feuille" />
            <span className="font-semibold">{t("ok")}</span>
          </>
        )}
      </div>

      {isError && (
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="border-prune text-prune mt-4 min-h-12 rounded-full border px-6 font-semibold disabled:opacity-60"
        >
          {t("retry")}
        </button>
      )}
    </section>
  );
}
