"use client";

import { Package } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { getOrders } from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";
import { formatMoney } from "@/lib/money";

/** Her purchases, or her sales (with a filter « to handle »). */
export function OrderList({
  role: initialRole = "buyer",
  showTabs = true,
}: {
  role?: "buyer" | "seller";
  showTabs?: boolean;
}) {
  const t = useTranslations("shop.orders");
  const tStatus = useTranslations("shop.status");
  const locale = useLocale();
  const [role, setRole] = useState(initialRole);
  const [active, setActive] = useState(initialRole === "seller");
  const query = useQuery({
    queryKey: ["orders", role, active],
    queryFn: () => getOrders(role, role === "seller" && active ? "active" : undefined),
  });
  const rows = query.data?.results ?? [];

  return (
    <div className="flex flex-col gap-4">
      {showTabs && (
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
                "min-h-12 rounded-full font-bold",
                role === key ? "bg-carte text-prune" : "text-prune-doux",
              )}
            >
              {key === "buyer" ? t("purchases") : t("sales")}
            </button>
          ))}
        </div>
      )}
      {role === "seller" && (
        <label className="flex min-h-12 items-center gap-3 font-bold">
          <input
            type="checkbox"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
            className="accent-hibiscus size-6"
          />
          {t("onlyActive")}
        </label>
      )}
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Package size={44} weight="duotone" />}
          title={role === "buyer" ? t("noPurchase") : t("noSale")}
          description={role === "buyer" ? t("noPurchaseHelp") : undefined}
          action={
            role === "buyer" ? (
              <Link href="/explore" className={buttonClasses({ size: "lg" })}>
                {t("explore")}
              </Link>
            ) : undefined
          }
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((order) => {
            const first = order.lines[0];
            return (
              <li key={order.id}>
                <Link
                  href={`/orders/${order.id}`}
                  className="border-trait hover:bg-poudre rounded-card flex min-h-16 items-center gap-3 border p-3"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                  <img
                    src={mediaSrc(first?.photo, "thumb")}
                    alt=""
                    className="bg-poudre size-14 shrink-0 rounded-xl object-cover"
                  />
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-bold">
                      {role === "buyer" ? order.shop.name : order.buyer.name}
                    </span>
                    <span className="text-small text-prune-doux truncate">
                      {t("line", {
                        reference: order.reference,
                        count: order.lines.length,
                      })}
                    </span>
                    <span className="text-small font-bold">{tStatus(order.status)}</span>
                  </span>
                  <span className="shrink-0 font-bold">
                    {formatMoney(order.total_minor, order.currency, locale)}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
