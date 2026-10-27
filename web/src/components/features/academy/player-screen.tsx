"use client";

import {
  ArrowLeft,
  CaretLeft,
  CaretRight,
  CloudArrowDown,
  Exam,
  FilePdf,
  Trash,
  WifiSlash,
} from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { lessonBlobUrl, offlineSupported, removeLesson, saveLesson } from "@/lib/academy/offline";
import { getLesson, savePosition, type LessonPlayback } from "@/lib/api/academy";
import { ApiError, hasSession } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { usePreferences } from "@/lib/preferences/preferences-provider";

import { Duration } from "./parts";

type Quality = "low" | "medium";
const SAVE_EVERY_SECONDS = 15;

/** A phone that saves data, or a slow network: the low quality first. */
function startQuality(dataSaver: boolean): Quality {
  if (dataSaver) return "low";
  const connection = (
    navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }
  ).connection;
  if (connection?.saveData || /(^|-)2g|3g/.test(connection?.effectiveType ?? "")) return "low";
  return "medium";
}

/** The player: one lesson, its resources, the next step (lesson or quiz). */
export function PlayerScreen({ slug, lessonId }: { slug: string; lessonId: string }) {
  const t = useTranslations("academy.player");
  const { dataSaver } = usePreferences();
  const query = useQuery({
    queryKey: ["academy-lesson", lessonId],
    queryFn: () => getLesson(lessonId),
    retry: false,
    staleTime: 30 * 60 * 1000,
  });
  const [offlineUrl, setOfflineUrl] = useState<string | null>(null);
  const [offlineChecked, setOfflineChecked] = useState(false);

  // A copy saved on the phone is used when the network does not answer.
  useEffect(() => {
    let url: string | null = null;
    void lessonBlobUrl(lessonId).then((found) => {
      url = found;
      setOfflineUrl(found);
      setOfflineChecked(true);
    });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [lessonId]);

  if (query.isPending && !offlineChecked) {
    return <Skeleton className="aspect-video w-full rounded-2xl" />;
  }
  if (!query.data) {
    if (offlineUrl) return <OfflineOnly slug={slug} url={offlineUrl} />;
    if (query.isPending) return <Skeleton className="aspect-video w-full rounded-2xl" />;
    const error = query.error;
    return (
      <div className="flex flex-col gap-4">
        <p role="alert" className="font-bold">
          {error instanceof ApiError ? error.message : t("error")}
        </p>
        <Link href={`/academie/${slug}`} className={buttonClasses({ variant: "secondary" })}>
          {t("backToCourse")}
        </Link>
      </div>
    );
  }
  return (
    <Lesson
      key={query.data.id}
      lesson={query.data}
      offlineUrl={offlineUrl}
      onOfflineChange={setOfflineUrl}
      dataSaver={dataSaver}
      refresh={async () => (await query.refetch()).data}
    />
  );
}

function OfflineOnly({ slug, url }: { slug: string; url: string }) {
  const t = useTranslations("academy.player");
  return (
    <div className="flex flex-col gap-4">
      <p className="bg-poudre flex items-center gap-2 rounded-2xl p-3 font-bold">
        <WifiSlash aria-hidden size={24} />
        {t("offlineCopy")}
      </p>
      <video src={url} controls playsInline className="bg-prune aspect-video w-full rounded-2xl" />
      <Link href={`/academie/${slug}`} className={buttonClasses({ variant: "secondary" })}>
        {t("backToCourse")}
      </Link>
    </div>
  );
}

function Lesson({
  lesson,
  offlineUrl,
  onOfflineChange,
  dataSaver,
  refresh,
}: {
  lesson: LessonPlayback;
  offlineUrl: string | null;
  onOfflineChange: (url: string | null) => void;
  dataSaver: boolean;
  refresh: () => Promise<LessonPlayback | undefined>;
}) {
  const t = useTranslations("academy.player");
  const toast = useToast();
  const video = useRef<HTMLVideoElement>(null);
  const [quality, setQuality] = useState<Quality>(() => startQuality(dataSaver));
  const [urls, setUrls] = useState(lesson.urls);
  const [ended, setEnded] = useState(false);
  const [online, setOnline] = useState(true);
  const lastSaved = useRef(0);
  const resumeAt = useRef(lesson.position_seconds);
  const signedIn = hasSession();

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const save = useCallback(
    (endedNow = false) => {
      const element = video.current;
      if (!element || !signedIn) return;
      const seconds = Math.floor(element.currentTime);
      lastSaved.current = seconds;
      savePosition(lesson.id, { seconds, ended: endedNow }).catch(() => {
        // a preview without the course, or no network: nothing to keep
      });
    },
    [lesson.id, signedIn],
  );

  useEffect(() => {
    const leave = () => {
      if (document.visibilityState === "hidden") save();
    };
    document.addEventListener("visibilitychange", leave);
    return () => document.removeEventListener("visibilitychange", leave);
  }, [save]);

  const source = !online && offlineUrl ? offlineUrl : (urls[quality] ?? urls.low ?? offlineUrl);

  const changeQuality = (next: Quality) => {
    resumeAt.current = Math.floor(video.current?.currentTime ?? 0);
    setQuality(next);
  };

  // A signed link lasts about an hour: a new one, at the same second.
  const renew = async () => {
    resumeAt.current = Math.floor(video.current?.currentTime ?? 0);
    const fresh = await refresh();
    if (fresh) setUrls(fresh.urls);
  };

  const after = lesson.next
    ? { href: `/academie/${lesson.course_slug}/lecon/${lesson.next}`, label: t("next") }
    : null;
  const quiz = lesson.quiz_after
    ? { href: `/academie/${lesson.course_slug}/quiz/${lesson.quiz_after}`, label: t("quiz") }
    : null;

  return (
    <article className="flex flex-col gap-5">
      <Link
        href={`/academie/${lesson.course_slug}`}
        className="text-prune-doux inline-flex min-h-12 items-center gap-2 self-start font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {lesson.course_title}
      </Link>
      {source ? (
        <video
          ref={video}
          key={source}
          src={source}
          poster={urls.poster ?? undefined}
          controls
          playsInline
          preload="metadata"
          className="bg-prune aspect-video w-full rounded-2xl"
          onLoadedMetadata={(event) => {
            const element = event.currentTarget;
            if (resumeAt.current > 0 && resumeAt.current < element.duration - 5) {
              element.currentTime = resumeAt.current;
            }
          }}
          onTimeUpdate={(event) => {
            const now = Math.floor(event.currentTarget.currentTime);
            if (Math.abs(now - lastSaved.current) >= SAVE_EVERY_SECONDS) save();
          }}
          onPause={() => save()}
          onEnded={() => {
            save(true);
            setEnded(true);
          }}
          onError={() => {
            if (online && source !== offlineUrl) void renew();
          }}
        />
      ) : (
        <p className="bg-poudre flex aspect-video items-center justify-center rounded-2xl p-4 text-center">
          {t("processing")}
        </p>
      )}

      {!online && (
        <p className="bg-poudre flex items-center gap-2 rounded-2xl p-3 font-bold">
          <WifiSlash aria-hidden size={24} />
          {offlineUrl ? t("offlineCopy") : t("offlineMissing")}
        </p>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="text-small text-prune-doux mb-1 font-bold">{t("quality")}</legend>
        <div className="bg-poudre grid grid-cols-2 rounded-full p-1">
          {(["low", "medium"] as const).map((value) => (
            <label
              key={value}
              className={cn(
                "flex min-h-12 cursor-pointer items-center justify-center rounded-full px-3 text-center font-bold",
                quality === value ? "bg-carte" : "text-prune-doux",
              )}
            >
              <input
                type="radio"
                name="quality"
                value={value}
                checked={quality === value}
                onChange={() => changeQuality(value)}
                className="sr-only"
              />
              {t(`qualities.${value}`)}
            </label>
          ))}
        </div>
      </fieldset>

      <header className="flex flex-col gap-2">
        <p className="text-small text-prune-doux font-bold">{lesson.module_title}</p>
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{lesson.title}</h1>
          <SpeakButton text={[lesson.title, lesson.description].filter(Boolean).join(". ")} />
        </div>
        <p className="text-prune-doux">
          <Duration seconds={lesson.duration_seconds} />
        </p>
        {lesson.description && <p className="whitespace-pre-line">{lesson.description}</p>}
      </header>

      {(ended || after || quiz) && (
        <div className="flex flex-col gap-3">
          {quiz ? (
            <Link
              href={quiz.href}
              className={buttonClasses({
                size: "lg",
                fullWidth: true,
                variant: ended ? "primary" : "secondary",
              })}
            >
              <Exam aria-hidden size={24} weight="bold" />
              {quiz.label}
            </Link>
          ) : after ? (
            <Link
              href={after.href}
              className={buttonClasses({
                size: "lg",
                fullWidth: true,
                variant: ended ? "primary" : "secondary",
              })}
            >
              {after.label}
              <CaretRight aria-hidden size={22} weight="bold" />
            </Link>
          ) : (
            <Link
              href={`/academie/${lesson.course_slug}`}
              className={buttonClasses({ size: "lg", fullWidth: true })}
            >
              {t("backToCourse")}
            </Link>
          )}
        </div>
      )}

      {lesson.resources.length > 0 && (
        <section aria-labelledby="lesson-resources" className="flex flex-col gap-2">
          <h2 id="lesson-resources" className="text-title font-bold">
            {t("resources")}
          </h2>
          <ul className="flex flex-col gap-2">
            {lesson.resources.map((resource) => (
              <li key={resource.id}>
                {resource.url ? (
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noreferrer"
                    className="border-trait bg-carte rounded-card flex min-h-14 items-center gap-3 border p-3 font-bold"
                  >
                    <FilePdf aria-hidden size={26} weight="duotone" className="text-hibiscus" />
                    {resource.title}
                  </a>
                ) : (
                  <span className="text-prune-doux">{resource.title}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {signedIn && offlineSupported() && urls.low && (
        <OfflineButton
          lesson={lesson}
          videoUrl={urls.low}
          saved={Boolean(offlineUrl)}
          onChange={onOfflineChange}
          onError={() => toast(t("downloadFailed"), "warning")}
        />
      )}

      {lesson.previous && (
        <Link
          href={`/academie/${lesson.course_slug}/lecon/${lesson.previous}`}
          className={buttonClasses({ variant: "quiet", className: "self-start" })}
        >
          <CaretLeft aria-hidden size={22} />
          {t("previous")}
        </Link>
      )}
    </article>
  );
}

function OfflineButton({
  lesson,
  videoUrl,
  saved,
  onChange,
  onError,
}: {
  lesson: LessonPlayback;
  videoUrl: string;
  saved: boolean;
  onChange: (url: string | null) => void;
  onError: () => void;
}) {
  const t = useTranslations("academy.player");
  const [share, setShare] = useState<number | null>(null);

  const download = async () => {
    setShare(0);
    try {
      await saveLesson(
        {
          id: lesson.id,
          title: lesson.title,
          courseTitle: lesson.course_title,
          courseSlug: lesson.course_slug,
        },
        videoUrl,
        setShare,
      );
      onChange(await lessonBlobUrl(lesson.id));
    } catch {
      onError();
    } finally {
      setShare(null);
    }
  };

  if (saved) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-feuille font-bold">{t("saved")}</p>
        <Button
          variant="quiet"
          onClick={() => {
            void removeLesson(lesson.id).then(() => onChange(null));
          }}
        >
          <Trash aria-hidden size={22} />
          {t("removeDownload")}
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="secondary"
        fullWidth
        disabled={share !== null}
        onClick={() => void download()}
      >
        <CloudArrowDown aria-hidden size={24} weight="bold" />
        {share === null ? t("download") : t("downloading", { percent: Math.round(share * 100) })}
      </Button>
      <p className="text-small text-prune-doux">{t("downloadHelp")}</p>
    </div>
  );
}
