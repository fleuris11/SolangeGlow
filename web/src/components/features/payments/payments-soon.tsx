import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

type Props = {
  /** What to do meanwhile, for this screen (a key of payments.soon). */
  meanwhile?: "shop" | "selection" | "course" | "pass" | "gift" | "boost" | "premium" | "salon";
  /** The way forward meanwhile (write, see the free courses...). */
  children?: ReactNode;
};

/**
 * Online payment is being opened by the owner (admin, switch « Payments closed »). Shown where a
 * payment would start, instead of the button that would start it: a service being switched on,
 * with what can be done meanwhile, never an error.
 */
export function PaymentsSoon({ meanwhile, children }: Props) {
  const t = useTranslations("payments.soon");
  return (
    <div
      role="status"
      className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-4"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="bg-poudre text-hibiscus grid size-12 shrink-0 place-items-center rounded-full"
        >
          <svg
            viewBox="0 0 256 256"
            className="size-6"
            fill="none"
            stroke="currentColor"
            strokeWidth="16"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="40" y="88" width="176" height="128" rx="16" />
            <path d="M88 88V64a40 40 0 0 1 80 0v24" />
            <circle cx="128" cy="152" r="12" />
          </svg>
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-2">
            <strong className="font-bold">{t("title")}</strong>
            <span className="bg-prune text-lait text-mention rounded-full px-3 py-0.5 font-bold">
              {t("badge")}
            </span>
          </span>
          <span className="text-prune-doux">{t(meanwhile ?? "text")}</span>
        </span>
      </div>
      {children}
    </div>
  );
}
