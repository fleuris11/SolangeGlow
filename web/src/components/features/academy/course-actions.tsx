"use client";

import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { refundCourse, takeCourse, type CourseDetail } from "@/lib/api/academy";
import { ApiError, hasSession } from "@/lib/api/client";
import { rememberReturnPath } from "@/lib/auth/return-path";
import { Link, usePathname, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { ProgressBar } from "./parts";

// The waiver sheet arrives only when she decides to buy (ADR-004).
const BuySheet = dynamic(() => import("./buy-sheet").then((m) => m.BuySheet));

type Icons = { play: ReactNode; buy: ReactNode; pass: ReactNode; done: ReactNode };

/** The one main action of the course page: start, buy, continue; and the refund. */
export function CourseActions({
  course,
  firstLesson,
  icons,
}: {
  course: CourseDetail;
  firstLesson: string | null;
  icons: Icons;
}) {
  const t = useTranslations("academy.course");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [buying, setBuying] = useState(false);
  const enrollment = course.enrollment;
  const lessonUrl = (id: string | null) => `/academie/${course.slug}/lecon/${id ?? firstLesson}`;

  const fail = (error: unknown) =>
    toast(error instanceof ApiError ? error.message : t("error"), "warning");

  const signInFirst = () => {
    rememberReturnPath(pathname);
    router.push("/auth?as=client");
  };

  const start = async () => {
    if (!hasSession()) return signInFirst();
    setBusy(true);
    try {
      await takeCourse(course.slug, { waiver: false });
      router.push(lessonUrl(null));
    } catch (error) {
      fail(error);
      setBusy(false);
    }
  };

  const refund = async () => {
    if (!enrollment) return;
    setBusy(true);
    try {
      await refundCourse(enrollment.id);
      toast(t("refunded"), "success");
      router.refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };

  if (course.is_trainer) {
    return (
      <div className="flex flex-col gap-3">
        <p className="bg-poudre rounded-2xl p-3 font-bold">{t("yours")}</p>
        {firstLesson && (
          <Link href={lessonUrl(null)} className={buttonClasses({ fullWidth: true })}>
            {icons.play}
            {t("watch")}
          </Link>
        )}
      </div>
    );
  }

  if (enrollment && enrollment.status === "active" && enrollment.can_watch) {
    return (
      <div className="flex flex-col gap-3">
        <ProgressBar percent={enrollment.progress_percent} label={t("progress")} />
        {enrollment.completed_at ? (
          <p className="text-feuille flex items-center gap-2 font-bold">
            {icons.done}
            {t("finished")}
          </p>
        ) : null}
        <Link
          href={lessonUrl(enrollment.last_lesson)}
          className={buttonClasses({ fullWidth: true })}
        >
          {icons.play}
          {enrollment.started ? t("continue") : t("startNow")}
        </Link>
        {enrollment.certificate && (
          <Link
            href="/academie/mes-formations"
            className={buttonClasses({ variant: "secondary", fullWidth: true })}
          >
            {t("certificate")}
          </Link>
        )}
        {enrollment.refund_until && (
          <div className="flex flex-col gap-2">
            <p className="text-small text-prune-doux">
              {t("refundUntil", {
                date: new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
                  new Date(enrollment.refund_until),
                ),
              })}
            </p>
            <Button variant="quiet" fullWidth disabled={busy} onClick={() => void refund()}>
              {t("refund")}
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (course.pricing === "pass" && !course.pass_offer.active) {
    return (
      <div className="flex flex-col gap-3">
        <p>{t("passOnly")}</p>
        <Link href="/academie/pass" className={buttonClasses({ fullWidth: true })}>
          {icons.pass}
          {t("takePass")}
        </Link>
      </div>
    );
  }

  if (course.pricing === "paid") {
    const price = formatMoney(course.price_minor, course.currency, locale);
    return (
      <div className="flex flex-col gap-3">
        <p className="text-small text-prune-doux">{t("paidHelp", { days: course.refund_days })}</p>
        <Button
          fullWidth
          disabled={busy}
          onClick={() => (hasSession() ? setBuying(true) : signInFirst())}
        >
          {icons.buy}
          {t("buy", { price })}
        </Button>
        {buying && (
          <BuySheet
            course={course}
            price={price}
            open={buying}
            onOpenChange={setBuying}
            onError={fail}
          />
        )}
      </div>
    );
  }

  return (
    <Button fullWidth disabled={busy || !firstLesson} onClick={() => void start()}>
      {icons.play}
      {course.pricing === "pass" ? t("startWithPass") : t("startFree")}
    </Button>
  );
}
