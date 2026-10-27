import { useTranslations } from "next-intl";

import { PriceTag } from "@/components/ui/price-tag";
import type { CourseCard } from "@/lib/api/academy";
import { cn } from "@/lib/cn";

/** « 12 min », « 1 h 05 »: the length of a lesson or a course. */
export function durationText(
  seconds: number,
  t: (key: "minutes" | "hours", values: Record<string, number | string>) => string,
) {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return t("minutes", { count: minutes });
  return t("hours", {
    hours: Math.floor(minutes / 60),
    minutes: String(minutes % 60).padStart(2, "0"),
  });
}

export function Duration({ seconds }: { seconds: number }) {
  const t = useTranslations("academy.duration");
  return <>{durationText(seconds, t)}</>;
}

/** Free, included in the pass, or its price. */
export function CoursePrice({ course, className }: { course: CourseCard; className?: string }) {
  const t = useTranslations("academy.pricing");
  if (course.pricing === "paid") {
    return (
      <PriceTag amountMinor={course.price_minor} currency={course.currency} className={className} />
    );
  }
  return (
    <span
      className={cn(
        "font-bold",
        course.pricing === "free" ? "text-feuille" : "text-prune",
        className,
      )}
    >
      {t(course.pricing)}
    </span>
  );
}

/** A bar and its number: the colour never carries the information alone. */
export function ProgressBar({ percent, label }: { percent: number; label: string }) {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  return (
    <div className="flex items-center gap-3">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        className="bg-poudre h-3 flex-1 overflow-hidden rounded-full"
      >
        <div className="bg-feuille h-full rounded-full" style={{ width: `${value}%` }} />
      </div>
      <span className="text-small w-12 shrink-0 text-right font-bold">{value} %</span>
    </div>
  );
}
