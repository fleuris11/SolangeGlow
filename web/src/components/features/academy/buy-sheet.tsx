"use client";

import { ShieldCheck } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import { SpeakButton } from "@/components/ui/speak-button";
import { takeCourse, type CourseDetail } from "@/lib/api/academy";

/** Buying a course: the waiver box (start now, no change of mind once a lesson is open). */
export function BuySheet({
  course,
  price,
  open,
  onOpenChange,
  onError,
}: {
  course: CourseDetail;
  price: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onError: (error: unknown) => void;
}) {
  const t = useTranslations("academy.buy");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const waiver = t("waiver", { days: course.refund_days });

  const pay = async () => {
    setBusy(true);
    try {
      const answer = await takeCourse(course.slug, { waiver: true, waiver_text: waiver });
      if (answer.checkout_url) window.location.assign(answer.checkout_url);
    } catch (error) {
      onError(error);
      setBusy(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={t("title")} description={course.title}>
      <div className="flex flex-col gap-4">
        <p className="bg-poudre flex items-start gap-3 rounded-2xl p-3">
          <ShieldCheck aria-hidden size={28} weight="duotone" className="text-feuille shrink-0" />
          <span>{t("safe", { days: course.refund_days })}</span>
        </p>
        <label className="border-trait flex min-h-14 cursor-pointer items-start gap-3 rounded-2xl border-2 p-3">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="accent-hibiscus mt-1 size-6 shrink-0"
          />
          <span>{waiver}</span>
        </label>
        <SpeakButton text={`${t("safe", { days: course.refund_days })} ${waiver}`} />
        <Button size="lg" fullWidth disabled={!agreed || busy} onClick={() => void pay()}>
          {t("pay", { price })}
        </Button>
      </div>
    </Sheet>
  );
}
