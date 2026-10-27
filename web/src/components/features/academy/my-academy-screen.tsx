"use client";

import {
  BookOpenText,
  Certificate,
  CloudArrowDown,
  DownloadSimple,
  GraduationCap,
  PlayCircle,
  Ticket,
  Trash,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import {
  listLessons,
  offlineSupported,
  removeLesson,
  type OfflineLesson,
} from "@/lib/academy/offline";
import { certificatePdfUrl, getMyAcademy } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";

import { ProgressBar } from "./parts";

/** « My courses »: going on, finished, certificates, lessons saved on the phone, the pass. */
export function MyAcademyScreen() {
  const t = useTranslations("academy.mine");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["academy-me"], queryFn: getMyAcademy });

  if (query.isPending) return <Skeleton className="h-80 rounded-2xl" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const { courses, academy_pass: academyPass } = query.data;
  const going = courses.filter(
    (c) => c.enrollment.status === "active" && !c.enrollment.completed_at,
  );
  const finished = courses.filter((c) => c.enrollment.completed_at);
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(new Date(value));

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <BookOpenText aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>

      {courses.length === 0 ? (
        <EmptyState
          icon={<GraduationCap size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
          action={
            <Link href="/academie" className={buttonClasses({})}>
              {t("explore")}
            </Link>
          }
        />
      ) : (
        <>
          {going.length > 0 && (
            <section aria-labelledby="mine-going" className="flex flex-col gap-3">
              <h2 id="mine-going" className="text-title font-bold">
                {t("going")}
              </h2>
              <ul className="flex flex-col gap-3">
                {going.map(({ course, enrollment }) => (
                  <li
                    key={course.id}
                    className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
                  >
                    <Link
                      href={`/academie/${course.slug}`}
                      className="text-lead font-bold underline"
                    >
                      {course.title}
                    </Link>
                    <ProgressBar percent={enrollment.progress_percent} label={t("progress")} />
                    {enrollment.can_watch ? (
                      <Link
                        href={
                          enrollment.last_lesson
                            ? `/academie/${course.slug}/lecon/${enrollment.last_lesson}`
                            : `/academie/${course.slug}`
                        }
                        className={buttonClasses({ fullWidth: true })}
                      >
                        <PlayCircle aria-hidden size={22} weight="fill" />
                        {enrollment.started ? t("continue") : t("start")}
                      </Link>
                    ) : (
                      <Link
                        href="/academie/pass"
                        className={buttonClasses({ variant: "secondary", fullWidth: true })}
                      >
                        <Ticket aria-hidden size={22} />
                        {t("passNeeded")}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {finished.length > 0 && (
            <section aria-labelledby="mine-finished" className="flex flex-col gap-3">
              <h2 id="mine-finished" className="text-title font-bold">
                {t("finished")}
              </h2>
              <ul className="flex flex-col gap-3">
                {finished.map(({ course, enrollment }) => (
                  <li
                    key={course.id}
                    className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-4"
                  >
                    <Link
                      href={`/academie/${course.slug}`}
                      className="text-lead font-bold underline"
                    >
                      {course.title}
                    </Link>
                    <p className="text-small text-prune-doux">
                      {t("finishedOn", { date: date(enrollment.completed_at as string) })}
                    </p>
                    {enrollment.certificate && (
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <a
                          href={certificatePdfUrl(enrollment.certificate)}
                          target="_blank"
                          rel="noreferrer"
                          className={buttonClasses({ fullWidth: true })}
                        >
                          <DownloadSimple aria-hidden size={22} weight="bold" />
                          {t("certificate")}
                        </a>
                        <Link
                          href={`/certificat/${enrollment.certificate}`}
                          className={buttonClasses({ variant: "secondary", fullWidth: true })}
                        >
                          <Certificate aria-hidden size={22} />
                          {t("checkPage")}
                        </Link>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <Downloads />

      <Link
        href="/academie/pass"
        className="bg-poudre rounded-card flex min-h-16 items-center gap-4 p-4"
      >
        <Ticket aria-hidden size={32} weight="duotone" className="text-hibiscus shrink-0" />
        <span className="flex flex-1 flex-col">
          <span className="font-bold">{academyPass.active ? t("passOn") : t("passOff")}</span>
          {academyPass.active && academyPass.current_period_end && (
            <span className="text-small text-prune-doux">
              {t("passUntil", { date: date(academyPass.current_period_end) })}
            </span>
          )}
        </span>
      </Link>
    </div>
  );
}

/** Lessons kept on the phone, with the space they take. */
function Downloads() {
  const t = useTranslations("academy.mine");
  const [lessons, setLessons] = useState<OfflineLesson[] | null>(null);
  useEffect(() => {
    void listLessons().then(setLessons);
  }, []);
  if (!offlineSupported() || lessons === null) return null;
  const megabytes = (bytes: number) => (bytes / (1024 * 1024)).toFixed(1);
  const total = lessons.reduce((sum, lesson) => sum + lesson.bytes, 0);

  return (
    <section aria-labelledby="mine-downloads" className="flex flex-col gap-3">
      <h2 id="mine-downloads" className="text-title flex items-center gap-2 font-bold">
        <CloudArrowDown aria-hidden size={26} weight="duotone" className="text-hibiscus" />
        {t("downloads")}
      </h2>
      {lessons.length === 0 ? (
        <p className="text-prune-doux">{t("noDownload")}</p>
      ) : (
        <>
          <p className="text-small text-prune-doux">{t("space", { size: megabytes(total) })}</p>
          <ul className="flex flex-col gap-2">
            {lessons.map((lesson) => (
              <li
                key={lesson.id}
                className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
              >
                <Link
                  href={`/academie/${lesson.courseSlug}/lecon/${lesson.id}`}
                  className="flex min-w-0 flex-1 flex-col"
                >
                  <span className="font-bold">{lesson.title}</span>
                  <span className="text-small text-prune-doux">
                    {lesson.courseTitle}, {t("size", { size: megabytes(lesson.bytes) })}
                  </span>
                </Link>
                <Button
                  variant="quiet"
                  onClick={() => {
                    void removeLesson(lesson.id).then(() =>
                      setLessons(lessons.filter((item) => item.id !== lesson.id)),
                    );
                  }}
                >
                  <Trash aria-hidden size={22} />
                  {t("remove")}
                </Button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
