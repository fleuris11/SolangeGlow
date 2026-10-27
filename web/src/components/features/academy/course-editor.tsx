"use client";

import {
  ArrowLeft,
  CheckCircle,
  CircleNotch,
  FilePdf,
  Image as ImageIcon,
  Plus,
  Trash,
  VideoCamera,
  WarningCircle,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { getTrades } from "@/lib/api/accounts";
import {
  addLesson,
  addModule,
  addQuestion,
  addResource,
  archiveCourse,
  deleteLesson,
  deleteModule,
  deleteQuestion,
  deleteResource,
  getStudioCourse,
  submitCourse,
  updateCourse,
  updateLesson,
  uploadAcademyFile,
  type AcademyPurpose,
  type StudioCourse,
  type StudioModule,
  type UploadedMedia,
} from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney, moneyInput, parseMoney } from "@/lib/money";

import { Duration } from "./parts";

const STEPS = ["about", "lessons", "quiz", "price", "send"] as const;
type Step = (typeof STEPS)[number];
const fieldClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-3 font-bold outline-none";

/** Guided creation of a course: about, lessons, quiz, price, sending to the team. */
export function CourseEditor({ courseId }: { courseId: string }) {
  const t = useTranslations("academy.editor");
  const [step, setStep] = useState<Step>("about");
  const query = useQuery({
    queryKey: ["academy-studio-course", courseId],
    queryFn: () => getStudioCourse(courseId),
    // While a video is being prepared, look again every few seconds.
    refetchInterval: (state) =>
      state.state.data?.modules.some((m) =>
        m.lessons.some((l) => l.video && ["pending", "processing"].includes(l.video.status)),
      )
        ? 5000
        : false,
  });

  if (query.isPending) return <Skeleton className="h-96 rounded-2xl" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const course = query.data;
  const index = STEPS.indexOf(step);
  const go = (next: number) =>
    setStep(STEPS[Math.max(0, Math.min(STEPS.length - 1, next))] as Step);

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/pro/academy"
        className="text-prune-doux inline-flex min-h-12 items-center gap-2 self-start font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {t("back")}
      </Link>
      <Stepper current={index + 1} total={STEPS.length} onBack={() => go(index - 1)} />
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t(`steps.${step}`)}</h1>
        <SpeakButton text={`${t(`steps.${step}`)}. ${t(`help.${step}`)}`} />
      </div>
      <p className="text-prune-doux">{t(`help.${step}`)}</p>
      {course.status === "in_review" && step !== "send" && (
        <p className="bg-poudre rounded-2xl p-3 font-bold">{t("inReview")}</p>
      )}
      {step === "about" && <AboutStep course={course} onNext={() => go(1)} />}
      {step === "lessons" && <LessonsStep course={course} />}
      {step === "quiz" && <QuizStep course={course} />}
      {step === "price" && <PriceStep course={course} onNext={() => go(4)} />}
      {step === "send" && <SendStep course={course} />}
      {step !== "send" && step !== "about" && step !== "price" && (
        <Button size="lg" fullWidth onClick={() => go(index + 1)}>
          {t("next")}
        </Button>
      )}
    </div>
  );
}

function useSave(courseId: string) {
  const t = useTranslations("academy.editor");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const run = async (action: () => Promise<StudioCourse | unknown>, message?: string) => {
    setBusy(true);
    try {
      const fresh = await action();
      if (fresh && typeof fresh === "object" && "modules" in fresh) {
        queryClient.setQueryData(["academy-studio-course", courseId], fresh);
      } else {
        await queryClient.invalidateQueries({ queryKey: ["academy-studio-course", courseId] });
      }
      if (message) toast(message, "success");
      return true;
    } catch (error) {
      toast(error instanceof ApiError ? error.message : t("error"), "warning");
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

// --- 1. About -------------------------------------------------------------------------------

function AboutStep({ course, onNext }: { course: StudioCourse; onNext: () => void }) {
  const t = useTranslations("academy.editor");
  const tLevels = useTranslations("academy.levels");
  const tLanguages = useTranslations("academy.languages");
  const trades = useQuery({ queryKey: ["trades"], queryFn: getTrades, staleTime: Infinity });
  const { busy, run } = useSave(course.id);
  const [values, setValues] = useState({
    title: course.title,
    summary: course.summary,
    description: course.description,
    trade: course.trade ?? "",
    level: course.level,
    language: course.language,
  });
  const set = (patch: Partial<typeof values>) => setValues({ ...values, ...patch });

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void run(() => updateCourse(course.id, values)).then((ok) => ok && onNext());
      }}
    >
      <Input
        label={t("title")}
        value={values.title}
        maxLength={120}
        required
        onChange={(e) => set({ title: e.target.value })}
      />
      <Input
        label={t("summary")}
        hint={t("summaryHint")}
        value={values.summary}
        maxLength={200}
        onChange={(e) => set({ summary: e.target.value })}
      />
      <label className="flex flex-col gap-1">
        <span className="font-bold">{t("description")}</span>
        <textarea
          value={values.description}
          maxLength={4000}
          rows={5}
          onChange={(event) => set({ description: event.target.value })}
          className="rounded-field bg-poudre focus:border-hibiscus border-2 border-transparent p-3 outline-none"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-bold">{t("trade")}</span>
        <select
          value={values.trade}
          onChange={(e) => set({ trade: e.target.value })}
          className={fieldClass}
        >
          <option value="">{t("noTrade")}</option>
          {(trades.data ?? []).map((trade) => (
            <option key={trade.key} value={trade.key}>
              {trade.name}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-bold">{t("level")}</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {(["beginner", "intermediate", "expert"] as const).map((level) => (
            <Choice
              key={level}
              name="level"
              checked={values.level === level}
              onChange={() => set({ level })}
            >
              {tLevels(level)}
            </Choice>
          ))}
        </div>
      </fieldset>
      <label className="flex flex-col gap-1">
        <span className="font-bold">{t("language")}</span>
        <select
          value={values.language}
          onChange={(e) => set({ language: e.target.value as typeof values.language })}
          className={fieldClass}
        >
          {(["fr", "en", "sk"] as const).map((language) => (
            <option key={language} value={language}>
              {tLanguages(language)}
            </option>
          ))}
        </select>
      </label>
      <CoverField course={course} />
      <Button type="submit" size="lg" fullWidth disabled={busy || !values.title.trim()}>
        {t("saveNext")}
      </Button>
    </form>
  );
}

function Choice({
  name,
  checked,
  onChange,
  children,
}: {
  name: string;
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
}) {
  return (
    <label
      className={cn(
        "flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border-2 px-3 font-bold",
        checked ? "border-hibiscus bg-poudre" : "border-trait",
      )}
    >
      <input
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
        className="accent-hibiscus size-6"
      />
      {children}
    </label>
  );
}

function CoverField({ course }: { course: StudioCourse }) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(course.id);
  const cover = course.cover?.urls.medium ?? course.cover?.urls.thumb;
  return (
    <div className="flex flex-col gap-2">
      <span className="font-bold">{t("cover")}</span>
      {cover && (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img
          src={cover}
          alt=""
          width={480}
          height={270}
          className="aspect-video w-full rounded-2xl object-cover"
        />
      )}
      <FilePick
        accept="image/*"
        purpose="course_cover"
        label={cover ? t("changeCover") : t("addCover")}
        icon={<ImageIcon aria-hidden size={22} />}
        disabled={busy}
        onUploaded={(media) => run(() => updateCourse(course.id, { cover_id: media.id }))}
      />
    </div>
  );
}

/** Picks a file and sends it, with a progress bar (videos can be big). */
function FilePick({
  accept,
  purpose,
  label,
  icon,
  disabled,
  onUploaded,
}: {
  accept: string;
  purpose: AcademyPurpose;
  label: string;
  icon: ReactNode;
  disabled?: boolean;
  onUploaded: (media: UploadedMedia) => unknown;
}) {
  const t = useTranslations("academy.editor");
  const toast = useToast();
  const [share, setShare] = useState<number | null>(null);
  return (
    <label
      className={cn(
        buttonClasses({ variant: "secondary", fullWidth: true }),
        "cursor-pointer",
        (disabled || share !== null) && "pointer-events-none opacity-50",
      )}
    >
      <input
        type="file"
        accept={accept}
        className="sr-only"
        disabled={disabled || share !== null}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          setShare(0);
          uploadAcademyFile(file, purpose, setShare)
            .then(onUploaded)
            .catch((error: unknown) =>
              toast(error instanceof ApiError ? error.message : t("uploadFailed"), "warning"),
            )
            .finally(() => setShare(null));
        }}
      />
      {icon}
      {share === null ? label : t("uploading", { percent: Math.round(share * 100) })}
    </label>
  );
}

// --- 2. Lessons ------------------------------------------------------------------------------

function LessonsStep({ course }: { course: StudioCourse }) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(course.id);
  const [title, setTitle] = useState("");
  return (
    <div className="flex flex-col gap-5">
      {course.modules.map((module, index) => (
        <ModuleCard key={module.id} course={course} module={module} number={index + 1} />
      ))}
      <form
        className="border-trait flex flex-col gap-3 rounded-2xl border-2 border-dashed p-4"
        onSubmit={(event) => {
          event.preventDefault();
          void run(() => addModule(course.id, title)).then((ok) => ok && setTitle(""));
        }}
      >
        <Input
          label={t("moduleTitle")}
          hint={t("moduleHint")}
          value={title}
          maxLength={120}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Button type="submit" variant="secondary" fullWidth disabled={busy || !title.trim()}>
          <Plus aria-hidden size={22} />
          {t("addModule")}
        </Button>
      </form>
    </div>
  );
}

function VideoState({
  video,
}: {
  video: StudioCourse["modules"][number]["lessons"][number]["video"];
}) {
  const t = useTranslations("academy.editor");
  if (!video) return <span className="text-alerte font-bold">{t("noVideo")}</span>;
  if (video.status === "ready") {
    return (
      <span className="text-feuille inline-flex items-center gap-1 font-bold">
        <CheckCircle aria-hidden size={18} weight="fill" />
        {t("videoReady")}
      </span>
    );
  }
  if (video.status === "rejected" || video.status === "failed") {
    return (
      <span className="text-alerte inline-flex items-center gap-1 font-bold">
        <WarningCircle aria-hidden size={18} weight="fill" />
        {video.error === "too_short" || video.error === "too_long"
          ? t("videoLength")
          : t("videoRefused")}
      </span>
    );
  }
  return (
    <span className="text-prune-doux inline-flex items-center gap-1 font-bold">
      <CircleNotch aria-hidden size={18} className="motion-safe:animate-spin" />
      {t("videoProcessing")}
    </span>
  );
}

function ModuleCard({
  course,
  module,
  number,
}: {
  course: StudioCourse;
  module: StudioModule;
  number: number;
}) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(course.id);
  const [adding, setAdding] = useState(module.lessons.length === 0);
  return (
    <section className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4">
      <div className="flex items-start gap-2">
        <h2 className="text-lead flex-1 font-bold">
          {t("module", { number, title: module.title })}
        </h2>
        <Button
          variant="quiet"
          disabled={busy}
          onClick={() => void run(() => deleteModule(module.id), t("deleted"))}
        >
          <Trash aria-hidden size={20} />
          {t("delete")}
        </Button>
      </div>
      <ol className="flex flex-col gap-3">
        {module.lessons.map((lesson) => (
          <li key={lesson.id} className="bg-poudre flex flex-col gap-2 rounded-xl p-3">
            <span className="font-bold">{lesson.title}</span>
            <span className="text-small flex flex-wrap items-center gap-x-3 gap-y-1">
              <VideoState video={lesson.video} />
              {lesson.duration_seconds > 0 && <Duration seconds={lesson.duration_seconds} />}
            </span>
            <label className="flex min-h-12 items-center gap-3">
              <input
                type="checkbox"
                checked={lesson.is_preview}
                disabled={busy}
                onChange={(event) =>
                  void run(() =>
                    updateLesson(lesson.id, {
                      title: lesson.title,
                      is_preview: event.target.checked,
                    }),
                  )
                }
                className="accent-hibiscus size-6"
              />
              {t("preview")}
            </label>
            {lesson.resources.map((resource) => (
              <span key={resource.id} className="flex items-center gap-2">
                <FilePdf aria-hidden size={20} className="text-hibiscus" />
                <span className="flex-1">{resource.title}</span>
                <Button
                  variant="quiet"
                  disabled={busy}
                  onClick={() => void run(() => deleteResource(resource.id))}
                >
                  <Trash aria-hidden size={18} />
                  {t("delete")}
                </Button>
              </span>
            ))}
            <ResourceForm courseId={course.id} lessonId={lesson.id} />
            <div className="flex flex-col gap-2 sm:flex-row">
              <FilePick
                accept="video/*"
                purpose="lesson_video"
                label={t("replaceVideo")}
                icon={<VideoCamera aria-hidden size={22} />}
                disabled={busy}
                onUploaded={(media) =>
                  run(() =>
                    updateLesson(lesson.id, {
                      title: lesson.title,
                      video_id: media.id,
                      is_preview: lesson.is_preview,
                    }),
                  )
                }
              />
              <Button
                variant="quiet"
                disabled={busy}
                onClick={() => void run(() => deleteLesson(lesson.id), t("deleted"))}
              >
                <Trash aria-hidden size={20} />
                {t("deleteLesson")}
              </Button>
            </div>
          </li>
        ))}
      </ol>
      {adding ? (
        <NewLesson courseId={course.id} moduleId={module.id} onDone={() => setAdding(false)} />
      ) : (
        <Button variant="secondary" fullWidth onClick={() => setAdding(true)}>
          <Plus aria-hidden size={22} />
          {t("addLesson")}
        </Button>
      )}
    </section>
  );
}

function NewLesson({
  courseId,
  moduleId,
  onDone,
}: {
  courseId: string;
  moduleId: string;
  onDone: () => void;
}) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(courseId);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [video, setVideo] = useState<UploadedMedia | null>(null);
  return (
    <form
      className="border-trait flex flex-col gap-3 rounded-xl border-2 border-dashed p-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!video) return;
        void run(() =>
          addLesson(moduleId, { title, description, video_id: video.id, is_preview: false }),
        ).then((ok) => ok && onDone());
      }}
    >
      <Input
        label={t("lessonTitle")}
        value={title}
        maxLength={120}
        required
        onChange={(e) => setTitle(e.target.value)}
      />
      <label className="flex flex-col gap-1">
        <span className="font-bold">{t("lessonDescription")}</span>
        <textarea
          value={description}
          maxLength={2000}
          rows={3}
          onChange={(event) => setDescription(event.target.value)}
          className="rounded-field bg-poudre focus:border-hibiscus border-2 border-transparent p-3 outline-none"
        />
      </label>
      {video ? (
        <p className="text-feuille flex items-center gap-2 font-bold">
          <CheckCircle aria-hidden size={22} weight="fill" />
          {t("videoSent")}
        </p>
      ) : (
        <>
          <FilePick
            accept="video/*"
            purpose="lesson_video"
            label={t("addVideo")}
            icon={<VideoCamera aria-hidden size={22} />}
            onUploaded={setVideo}
          />
          <p className="text-small text-prune-doux">{t("videoHint")}</p>
        </>
      )}
      <Button type="submit" fullWidth disabled={busy || !title.trim() || !video}>
        {t("saveLesson")}
      </Button>
    </form>
  );
}

function ResourceForm({ courseId, lessonId }: { courseId: string; lessonId: string }) {
  const t = useTranslations("academy.editor");
  const { run } = useSave(courseId);
  const [title, setTitle] = useState("");
  return (
    <div className="flex flex-col gap-2">
      <Input
        label={t("resourceTitle")}
        value={title}
        maxLength={120}
        onChange={(e) => setTitle(e.target.value)}
      />
      <FilePick
        accept="application/pdf"
        purpose="course_resource"
        label={t("addResource")}
        icon={<FilePdf aria-hidden size={22} />}
        disabled={!title.trim()}
        onUploaded={(media) =>
          run(() => addResource(lessonId, { title, file_id: media.id })).then(
            (ok) => ok && setTitle(""),
          )
        }
      />
    </div>
  );
}

// --- 3. Quiz ---------------------------------------------------------------------------------

function QuizStep({ course }: { course: StudioCourse }) {
  const t = useTranslations("academy.editor");
  if (course.modules.length === 0)
    return <p className="bg-poudre rounded-2xl p-3">{t("quizNoModule")}</p>;
  return (
    <div className="flex flex-col gap-5">
      {course.modules.map((module, index) => (
        <QuizModule key={module.id} course={course} module={module} number={index + 1} />
      ))}
    </div>
  );
}

function QuizModule({
  course,
  module,
  number,
}: {
  course: StudioCourse;
  module: StudioModule;
  number: number;
}) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(course.id);
  const [text, setText] = useState("");
  const [choices, setChoices] = useState(["", ""]);
  const [correct, setCorrect] = useState(0);
  const filled = choices.filter((choice) => choice.trim());

  return (
    <section className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4">
      <h2 className="text-lead font-bold">{t("module", { number, title: module.title })}</h2>
      {module.questions.length === 0 && <p className="text-prune-doux">{t("noQuestion")}</p>}
      <ol className="flex flex-col gap-2">
        {module.questions.map((question) => (
          <li key={question.id} className="bg-poudre flex items-start gap-2 rounded-xl p-3">
            <span className="flex flex-1 flex-col">
              <span className="font-bold">{question.text}</span>
              <span className="text-small">
                {t("rightAnswer", { answer: question.choices[question.correct] ?? "" })}
              </span>
            </span>
            <Button
              variant="quiet"
              disabled={busy}
              onClick={() => void run(() => deleteQuestion(question.id))}
            >
              <Trash aria-hidden size={18} />
              {t("delete")}
            </Button>
          </li>
        ))}
      </ol>
      <form
        className="border-trait flex flex-col gap-3 rounded-xl border-2 border-dashed p-3"
        onSubmit={(event) => {
          event.preventDefault();
          void run(() => addQuestion(module.id, { text, choices: filled, correct })).then((ok) => {
            if (!ok) return;
            setText("");
            setChoices(["", ""]);
            setCorrect(0);
          });
        }}
      >
        <Input
          label={t("question")}
          value={text}
          maxLength={300}
          onChange={(e) => setText(e.target.value)}
        />
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 font-bold">{t("answers")}</legend>
          {choices.map((choice, position) => (
            <div key={position} className="flex items-center gap-2">
              <input
                type="radio"
                name={`correct-${module.id}`}
                checked={correct === position}
                onChange={() => setCorrect(position)}
                aria-label={t("markRight", { number: position + 1 })}
                className="accent-hibiscus size-6 shrink-0"
              />
              <input
                value={choice}
                maxLength={200}
                aria-label={t("answer", { number: position + 1 })}
                onChange={(event) =>
                  setChoices(choices.map((item, i) => (i === position ? event.target.value : item)))
                }
                className="rounded-field bg-poudre focus:border-hibiscus min-h-12 flex-1 border-2 border-transparent px-3 outline-none"
              />
            </div>
          ))}
          <p className="text-small text-prune-doux">{t("answersHint")}</p>
          {choices.length < 4 && (
            <Button variant="quiet" onClick={() => setChoices([...choices, ""])}>
              <Plus aria-hidden size={20} />
              {t("addAnswer")}
            </Button>
          )}
        </fieldset>
        <Button
          type="submit"
          variant="secondary"
          fullWidth
          disabled={busy || !text.trim() || filled.length < 2 || !choices[correct]?.trim()}
        >
          {t("addQuestion")}
        </Button>
      </form>
    </section>
  );
}

// --- 4. Price --------------------------------------------------------------------------------

function PriceStep({ course, onNext }: { course: StudioCourse; onNext: () => void }) {
  const t = useTranslations("academy.editor");
  const tPricing = useTranslations("academy.pricing");
  const locale = useLocale();
  const { busy, run } = useSave(course.id);
  const [pricing, setPricing] = useState(course.pricing);
  const [price, setPrice] = useState(
    course.price_minor ? moneyInput(course.price_minor, course.currency, locale) : "",
  );
  const amount = parseMoney(price, course.currency);
  const options = course.trainer.platform
    ? (["free", "paid", "pass"] as const)
    : (["free", "paid"] as const);
  const limits = t("priceLimits", {
    min: formatMoney(course.price_min, course.currency, locale),
    max: formatMoney(course.price_max, course.currency, locale),
  });

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void run(() =>
          updateCourse(course.id, { pricing, price_minor: pricing === "paid" ? (amount ?? 0) : 0 }),
        ).then((ok) => ok && onNext());
      }}
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-bold">{t("pricing")}</legend>
        {options.map((option) => (
          <Choice
            key={option}
            name="pricing"
            checked={pricing === option}
            onChange={() => setPricing(option)}
          >
            {tPricing(option)}
          </Choice>
        ))}
      </fieldset>
      {pricing === "paid" && (
        <Input
          label={t("price", { currency: course.currency === "XOF" ? "FCFA" : "€" })}
          hint={`${limits} ${t("commission")}`}
          inputMode="decimal"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
      )}
      {!course.trainer.platform && <p className="text-small text-prune-doux">{t("passLater")}</p>}
      <Button type="submit" size="lg" fullWidth disabled={busy || (pricing === "paid" && !amount)}>
        {t("saveNext")}
      </Button>
    </form>
  );
}

// --- 5. Send ---------------------------------------------------------------------------------

function SendStep({ course }: { course: StudioCourse }) {
  const t = useTranslations("academy.editor");
  const { busy, run } = useSave(course.id);
  const lessons = course.modules.flatMap((module) => module.lessons);
  const checks = [
    { ok: Boolean(course.title.trim()), label: t("checks.title") },
    {
      ok: lessons.length > 0 && course.modules.every((m) => m.lessons.length > 0),
      label: t("checks.lessons"),
    },
    {
      ok: lessons.length > 0 && lessons.every((l) => l.video?.status === "ready"),
      label: t("checks.videos"),
    },
    {
      ok: course.modules.some((m) => m.questions.length > 0),
      label: t("checks.quiz"),
      optional: true,
    },
  ];
  const ready = checks.every((check) => check.ok || check.optional);
  const platform = course.trainer.platform;

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-2">
        {checks.map((check) => (
          <li key={check.label} className="flex items-center gap-2">
            {check.ok ? (
              <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille shrink-0" />
            ) : (
              <WarningCircle
                aria-hidden
                size={24}
                weight="fill"
                className={cn("shrink-0", check.optional ? "text-prune-doux" : "text-alerte")}
              />
            )}
            <span>
              {check.label}
              {check.optional && !check.ok && `, ${t("optional")}`}
            </span>
          </li>
        ))}
      </ul>
      <p className="bg-poudre rounded-2xl p-3 font-bold">{t(`state.${course.status}`)}</p>
      {course.status === "rejected" && course.review_note && (
        <p className="border-alerte rounded-2xl border-2 p-3">
          {t("note", { note: course.review_note })}
        </p>
      )}
      {(course.status === "draft" || course.status === "rejected") && (
        <Button
          size="lg"
          fullWidth
          disabled={busy || !ready}
          onClick={() =>
            void run(() => submitCourse(course.id), platform ? t("published") : t("sent"))
          }
        >
          {platform ? t("publish") : t("send")}
        </Button>
      )}
      {course.status === "published" && (
        <>
          <Link
            href={`/academie/${course.slug}`}
            className={buttonClasses({ size: "lg", fullWidth: true })}
          >
            {t("seePage")}
          </Link>
          <Button
            variant="quiet"
            fullWidth
            disabled={busy}
            onClick={() => void run(() => archiveCourse(course.id), t("archived"))}
          >
            {t("archive")}
          </Button>
        </>
      )}
    </div>
  );
}
