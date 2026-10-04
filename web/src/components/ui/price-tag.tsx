import { useLocale } from "next-intl";

import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/money";

type Props = {
  amountMinor: number;
  currency: string;
  /** "from" adds a translated prefix such as "dès". */
  prefix?: string;
  size?: "md" | "lg";
  className?: string;
};

/** A complete, explicit price: "15 000 FCFA", "25,00 €". */
export function PriceTag({ amountMinor, currency, prefix, size = "md", className }: Props) {
  const locale = useLocale();
  return (
    <span className={cn("font-bold whitespace-nowrap", size === "lg" && "text-title", className)}>
      {prefix && <span className="text-prune-doux font-normal">{prefix} </span>}
      {formatMoney(amountMinor, currency, locale)}
    </span>
  );
}
