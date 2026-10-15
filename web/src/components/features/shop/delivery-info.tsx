import { Moped, Storefront, Truck } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api/client";
import { formatMoney } from "@/lib/money";

type Delivery = Schemas["Delivery"];

/** How the shop hands over: pick-up, her own delivery, a partner (with the fees per zone). */
export function DeliveryInfo({ delivery, currency }: { delivery: Delivery; currency: string }) {
  const t = useTranslations("shop.delivery");
  const locale = useLocale();
  const zones = (mode: "seller" | "partner") =>
    delivery.zones
      .filter((zone) => zone.mode === mode)
      .map((zone) => `${zone.name} : ${formatMoney(zone.fee_minor, currency, locale)}`);
  const rows = [
    delivery.pickup && {
      key: "pickup",
      icon: <Storefront aria-hidden size={24} weight="duotone" />,
      title: t("pickup"),
      lines: [t("pickupFree"), delivery.pickup_note].filter(Boolean),
    },
    delivery.seller_delivery && {
      key: "seller",
      icon: <Moped aria-hidden size={24} weight="duotone" />,
      title: t("seller"),
      lines: zones("seller"),
    },
    delivery.partner_delivery && {
      key: "partner",
      icon: <Truck aria-hidden size={24} weight="duotone" />,
      title: delivery.partner_name
        ? t("partnerNamed", { name: delivery.partner_name })
        : t("partner"),
      lines: zones("partner"),
    },
  ].filter((row): row is Exclude<typeof row, false> => Boolean(row));

  return (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.key} className="flex gap-3">
          <span className="text-hibiscus mt-0.5 shrink-0">{row.icon}</span>
          <span className="flex flex-col">
            <span className="font-bold">{row.title}</span>
            {row.lines.map((line) => (
              <span key={line} className="text-small text-prune-doux">
                {line}
              </span>
            ))}
          </span>
        </li>
      ))}
    </ul>
  );
}
