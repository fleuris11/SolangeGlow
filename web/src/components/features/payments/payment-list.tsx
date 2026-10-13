"use client";

import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { getPayments } from "@/lib/api/payments";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

/** Her purchases and her sales, newest first. */
export function PaymentList({ initialRole = "buyer" }: { initialRole?: "buyer" | "seller" }) {
  const t = useTranslations("payments.list");
  const tStatus = useTranslations("payments.status");
  const locale = useLocale();
  const [role, setRole] = useState(initialRole);
  const query = useQuery({ queryKey: ["payments", role], queryFn: () => getPayments(role) });
  const rows = query.data?.results ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label={t("tabs")}
        className="bg-poudre grid grid-cols-2 rounded-full p-1"
      >
        {(["buyer", "seller"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={role === key}
            onClick={() => setRole(key)}
            className={cn(
              "min-h-12 rounded-full px-3 font-bold",
              role === key ? "bg-carte text-prune shadow-sm" : "text-prune-doux",
            )}
          >
            {key === "buyer" ? t("purchases") : t("sales")}
          </button>
        ))}
      </div>
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <p className="text-prune-doux py-8 text-center">
          {role === "buyer" ? t("noPurchase") : t("noSale")}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((payment) => (
            <li key={payment.id}>
              <Link
                href={`/payments/${payment.id}`}
                className="border-trait hover:bg-poudre rounded-card flex min-h-16 items-center justify-between gap-3 border p-4"
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-bold">{payment.description}</span>
                  <span className="text-small text-prune-doux">
                    {t("line", { reference: payment.reference, status: tStatus(payment.status) })}
                  </span>
                </span>
                <span className="shrink-0 font-bold">
                  {formatMoney(payment.total_minor, payment.currency, locale)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
