"use client";

import { ArrowLeft } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";

type Props = {
  /** 1-based index of the current step. */
  current: number;
  total: number;
  /** Shown when going back is possible. */
  onBack?: () => void;
};

/** Shows where we are in a journey ("Step 1 of 3"), with a way back. */
export function Stepper({ current, total, onBack }: Props) {
  const t = useTranslations("stepper");
  return (
    <div className="flex items-center gap-3">
      {onBack && current > 1 && (
        <button
          type="button"
          onClick={onBack}
          aria-label={t("back")}
          className="hover:bg-poudre -ml-2 inline-flex size-12 items-center justify-center rounded-full"
        >
          <ArrowLeft aria-hidden size={24} />
        </button>
      )}
      <div className="flex flex-1 flex-col gap-2">
        <p className="text-small font-bold">{t("progress", { current, total })}</p>
        <ol className="flex gap-2" aria-hidden>
          {Array.from({ length: total }, (_, index) => (
            <li
              key={index}
              className={cn(
                "h-2 flex-1 rounded-full transition-colors duration-200",
                index < current ? "bg-hibiscus" : "bg-trait",
              )}
            />
          ))}
        </ol>
      </div>
    </div>
  );
}
