"use client";

import { Broadcast, ChalkboardTeacher, Plus, X } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { cancelLive, createCourse, getStudio, planLive, type Studio } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

const STATUS_TONE: Record<string, string> = {
  draft: "bg-poudre",
  in_review: "bg-or text-sur-or",
  published: "border-feuille text-feuille border-2",
  rejected: "border-alerte border-2",
  archived: "bg-poudre",
};

/** The trainer space: her courses with their numbers, a new course, her lives. */
export function StudioScreen() {
  const t = useTranslations("academy.studio");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["academy-studio"], queryFn: getStudio });
  const [creating, setCreating] = useState(false);
  const [planning, setPlanning] = useState(false);

  if (query.isPending) return <Skeleton className="h-80 rounded-2xl" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const studio = query.data;
  if (!studio.is_pro && !studio.can_platform) {
    return (
      <EmptyState
        icon={<ChalkboardTeacher size={44} weight="duotone" />}
        title={t("notPro")}
        description={t("notProHelp")}
        action={
          <Link href="/pro/start" className={buttonClasses({})}>
            {t("becomePro")}
          </Link>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <ChalkboardTeacher aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={`${t("title")}. ${t("intro")}`} />
      </div>
      <p>{t("intro")}</p>
      {!studio.open ? (
        <p className="bg-poudre rounded-2xl p-3 font-bold">{t("closed")}</p>
      ) : (
        <Button size="lg" fullWidth onClick={() => setCreating(true)}>
          <Plus aria-hidden size={24} weight="bold" />
          {t("new")}
        </Button>
      )}

      <section aria-labelledby="studio-courses" className="flex flex-col gap-3">
        <h2 id="studio-courses" className="text-title font-bold">
          {t("courses")}
        </h2>
        {studio.courses.length === 0 ? (
          <p className="text-prune-doux">{t("noCourse")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {studio.courses.map((course) => (
              <li
                key={course.id}
                className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-lead flex-1 font-bold">{course.title}</span>
                  <span
                    className={cn(
                      "text-small rounded-full px-3 py-1 font-bold",
                      STATUS_TONE[course.status],
                    )}
                  >
                    {t(`status.${course.status}`)}
                  </span>
                </div>
                {course.trainer.platform && (
                  <p className="text-small text-prune-doux">{t("platform")}</p>
                )}
                {course.status === "rejected" && course.review_note && (
                  <p className="text-small">{t("note", { note: course.review_note })}</p>
                )}
                <dl className="grid grid-cols-2 gap-2 text-center">
                  <Stat label={t("students")} value={String(course.stats.students)} />
                  <Stat label={t("finished")} value={`${course.stats.completion_percent} %`} />
                  <Stat
                    wide
                    label={t("earned")}
                    value={formatMoney(course.stats.earned_minor, course.currency, locale)}
                  />
                </dl>
                <Link
                  href={`/pro/academy/${course.id}`}
                  className={buttonClasses({ variant: "secondary", fullWidth: true })}
                >
                  {t("edit")}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="studio-lives" className="flex flex-col gap-3">
        <h2 id="studio-lives" className="text-title flex items-center gap-2 font-bold">
          <Broadcast aria-hidden size={26} weight="duotone" className="text-hibiscus" />
          {t("lives")}
        </h2>
        {studio.lives_open ? (
          <Button variant="secondary" fullWidth onClick={() => setPlanning(true)}>
            <Plus aria-hidden size={22} />
            {t("planLive")}
          </Button>
        ) : (
          <p className="text-prune-doux">{t("livesClosed")}</p>
        )}
        <LiveList lives={studio.lives} />
      </section>

      {creating && <NewCourseSheet studio={studio} onClose={() => setCreating(false)} />}
      {planning && <PlanLiveSheet studio={studio} onClose={() => setPlanning(false)} />}
    </div>
  );
}

function Stat({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={cn("bg-poudre flex flex-col rounded-xl p-2", wide && "col-span-2")}>
      <dt className="text-small text-prune-doux">{label}</dt>
      <dd className="font-bold break-words">{value}</dd>
    </div>
  );
}

function LiveList({ lives }: { lives: Studio["lives"] }) {
  const t = useTranslations("academy.studio");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  if (lives.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2">
      {lives.map((live) => (
        <li
          key={live.id}
          className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-3 sm:flex-row sm:items-center"
        >
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="font-bold">{live.title}</span>
            <span className="text-small text-prune-doux">
              {new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
                new Date(live.starts_at),
              )}
              , {t(`liveStatus.${live.status}`)},{" "}
              {t("registeredCount", { count: live.capacity - live.places_left })}
            </span>
          </span>
          {live.status === "scheduled" && (
            <Button
              variant="quiet"
              onClick={() => {
                cancelLive(live.id)
                  .then(() => queryClient.invalidateQueries({ queryKey: ["academy-studio"] }))
                  .catch((error: unknown) =>
                    toast(error instanceof ApiError ? error.message : t("error"), "warning"),
                  );
              }}
            >
              <X aria-hidden size={20} />
              {t("cancelLive")}
            </Button>
          )}
        </li>
      ))}
    </ul>
  );
}

function NewCourseSheet({ studio, onClose }: { studio: Studio; onClose: () => void }) {
  const t = useTranslations("academy.studio");
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState(!studio.is_pro);
  const [country, setCountry] = useState("BJ");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      const course = await createCourse({ title, platform, country: platform ? country : "" });
      router.push(`/pro/academy/${course.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("error"));
      setBusy(false);
    }
  };

  return (
    <Sheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("new")}
      description={t("newHelp")}
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <Input
          label={t("courseTitle")}
          value={title}
          maxLength={120}
          required
          onChange={(e) => setTitle(e.target.value)}
          error={error ?? undefined}
        />
        {studio.can_platform && (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 font-bold">{t("forWhom")}</legend>
            {studio.is_pro && (
              <label className="flex min-h-12 items-center gap-3">
                <input
                  type="radio"
                  checked={!platform}
                  onChange={() => setPlatform(false)}
                  className="accent-hibiscus size-6"
                />
                {t("mine")}
              </label>
            )}
            <label className="flex min-h-12 items-center gap-3">
              <input
                type="radio"
                checked={platform}
                onChange={() => setPlatform(true)}
                className="accent-hibiscus size-6"
              />
              {t("platformCourse")}
            </label>
            {platform && (
              <label className="flex flex-col gap-1">
                <span className="text-small text-prune-doux font-bold">{t("country")}</span>
                <select
                  value={country}
                  onChange={(event) => setCountry(event.target.value)}
                  className="rounded-field bg-poudre min-h-14 px-3 font-bold"
                >
                  <option value="BJ">{t("countries.BJ")}</option>
                  <option value="FR">{t("countries.FR")}</option>
                </select>
              </label>
            )}
          </fieldset>
        )}
        <Button type="submit" size="lg" fullWidth disabled={busy || !title.trim()}>
          {t("create")}
        </Button>
      </form>
    </Sheet>
  );
}

function PlanLiveSheet({ studio, onClose }: { studio: Studio; onClose: () => void }) {
  const t = useTranslations("academy.studio");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [values, setValues] = useState({
    title: "",
    description: "",
    startsAt: "",
    duration: 60,
    capacity: 50,
    courseId: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (patch: Partial<typeof values>) => setValues({ ...values, ...patch });

  const plan = async () => {
    setBusy(true);
    setError(null);
    try {
      await planLive({
        title: values.title,
        description: values.description,
        starts_at: new Date(values.startsAt).toISOString(),
        duration_minutes: values.duration,
        capacity: values.capacity,
        course_id: values.courseId || null,
        platform: !studio.is_pro,
      });
      await queryClient.invalidateQueries({ queryKey: ["academy-studio"] });
      toast(t("livePlanned"), "success");
      onClose();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("error"));
      setBusy(false);
    }
  };

  return (
    <Sheet
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("planLive")}
      description={t("planLiveHelp")}
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void plan();
        }}
      >
        <Input
          label={t("liveTitle")}
          value={values.title}
          maxLength={120}
          required
          onChange={(e) => set({ title: e.target.value })}
        />
        <Input
          label={t("liveWhen")}
          type="datetime-local"
          value={values.startsAt}
          required
          onChange={(e) => set({ startsAt: e.target.value })}
        />
        <Input
          label={t("liveLength")}
          type="number"
          min={15}
          max={240}
          value={values.duration}
          onChange={(e) => set({ duration: Number(e.target.value) })}
        />
        <Input
          label={t("livePlaces")}
          type="number"
          min={1}
          max={10000}
          value={values.capacity}
          onChange={(e) => set({ capacity: Number(e.target.value) })}
        />
        {studio.courses.length > 0 && (
          <label className="flex flex-col gap-1">
            <span className="font-bold">{t("liveCourse")}</span>
            <select
              value={values.courseId}
              onChange={(event) => set({ courseId: event.target.value })}
              className="rounded-field bg-poudre min-h-14 px-3 font-bold"
            >
              <option value="">{t("noLinkedCourse")}</option>
              {studio.courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </select>
            <span className="text-small text-prune-doux">{t("liveCourseHelp")}</span>
          </label>
        )}
        <label className="flex flex-col gap-1">
          <span className="font-bold">{t("liveDescription")}</span>
          <textarea
            value={values.description}
            maxLength={2000}
            rows={3}
            onChange={(event) => set({ description: event.target.value })}
            className="rounded-field bg-poudre focus:border-hibiscus border-2 border-transparent p-3 outline-none"
          />
        </label>
        {error && (
          <p role="alert" className="text-alerte font-bold">
            {error}
          </p>
        )}
        <Button
          type="submit"
          size="lg"
          fullWidth
          disabled={busy || !values.title.trim() || !values.startsAt}
        >
          {t("planLiveCta")}
        </Button>
      </form>
    </Sheet>
  );
}
