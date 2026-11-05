import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

type Props = {
  /** What to do meanwhile, for this screen (a key of payments.soon). */
  meanwhile?: "shop" | "selection" | "course" | "pass" | "gift" | "boost" | "premium" | "salon";
  /** The way forward meanwhile (write, see the free courses...). */
  children?: ReactNode;
};

/**
 * Free launch: online payment is closed by the owner (admin, switch « Payments closed »).
 * Shown where a payment would start, instead of the button that would start it.
 */
export function PaymentsSoon({ meanwhile, children }: Props) {
  const t = useTranslations("payments.soon");
  return (
    <div role="status" className="bg-poudre rounded-card flex flex-col gap-3 p-4">
      <p className="flex items-start gap-3">
        <svg
          aria-hidden
          viewBox="0 0 256 256"
          className="mt-0.5 size-6 shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth="16"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="128" cy="128" r="96" />
          <polyline points="128 72 128 128 184 128" />
        </svg>
        <span className="flex flex-col gap-1">
          <strong className="font-semibold">{t("title")}</strong>
          <span>{t(meanwhile ?? "text")}</span>
        </span>
      </p>
      {children}
    </div>
  );
}
