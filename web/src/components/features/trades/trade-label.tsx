import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";

import { TradeIcon, type Trade } from "./trade-icon";

/** Trade pictogram + translated name. */
export function TradeLabel({
  trade,
  size = 20,
  className,
}: {
  trade: Trade;
  size?: number;
  className?: string;
}) {
  const t = useTranslations("trades");
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      <TradeIcon trade={trade} size={size} className="text-hibiscus shrink-0" />
      {t(trade)}
    </span>
  );
}
