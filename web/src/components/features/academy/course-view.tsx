import {
  CheckCircle,
  Clock,
  Exam,
  GraduationCap,
  LockSimple,
  PlayCircle,
  SealCheck,
  ShoppingBag,
  Ticket,
  UsersThree,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import { SpeakButton } from "@/components/ui/speak-button";
import type { CourseDetail } from "@/lib/api/academy";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { CourseActions } from "./course-actions";
import { CoursePrice, Duration } from "./parts";

/** A course: what it teaches, its programme, who teaches it, and how to start. */
export function CourseView({ course }: { course: CourseDetail }) {
  const t = useTranslations("academy.course");
  const tLevels = useTranslations("academy.levels");
  const tLanguages = useTranslations("academy.languages");
  const cover = mediaSrc(course.cover, "large", "medium");
  const enrollment = course.enrollment;
  const canWatch = Boolean(enrollment?.can_watch) || course.is_trainer;
  const firstLesson = course.modules[0]?.lessons[0]?.id ?? null;

  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-4">
        <span className="bg-poudre text-hibiscus flex aspect-video items-center justify-center overflow-hidden rounded-2xl">
          {cover ? (
            // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
            <img src={cover} alt="" width={960} height={540} className="size-full object-cover" />
          ) : (
            <GraduationCap aria-hidden size={72} weight="duotone" />
          )}
        </span>
        {course.trade_name && (
          <span className="text-small text-prune-doux font-bold">{course.trade_name}</span>
        )}
        <div className="flex items-start gap-2">
          <h1 className="font-display text-headline flex-1 font-black">{course.title}</h1>
          <SpeakButton text={[course.title, course.summary].filter(Boolean).join(". ")} />
        </div>
        {course.summary && <p className="text-lead">{course.summary}</p>}
        <ul className="text-prune-doux flex flex-wrap gap-x-4 gap-y-2">
          <li>{tLevels(course.level)}</li>
          <li>{tLanguages(course.language)}</li>
          <li className="inline-flex items-center gap-1">
            <PlayCircle aria-hidden size={20} />
            {t("lessons", { count: course.lessons_count })}
          </li>
          {course.duration_seconds > 0 && (
            <li className="inline-flex items-center gap-1">
              <Clock aria-hidden size={20} />
              <Duration seconds={course.duration_seconds} />
            </li>
          )}
          {course.students_count > 0 && (
            <li className="inline-flex items-center gap-1">
              <UsersThree aria-hidden size={20} />
              {t("students", { count: course.students_count })}
            </li>
          )}
        </ul>
        <p className="text-title">
          <CoursePrice course={course} />
        </p>
      </header>

      <CourseActions
        course={course}
        firstLesson={firstLesson}
        icons={{
          play: <PlayCircle aria-hidden size={24} weight="fill" />,
          buy: <ShoppingBag aria-hidden size={24} weight="bold" />,
          pass: <Ticket aria-hidden size={24} weight="bold" />,
          done: <CheckCircle aria-hidden size={24} weight="fill" />,
        }}
      />

      <section aria-labelledby="course-trainer" className="flex flex-col gap-3">
        <h2 id="course-trainer" className="text-title font-bold">
          {t("trainer")}
        </h2>
        <div className="flex items-center gap-3">
          <Avatar
            name={course.trainer.name}
            src={mediaSrc(course.trainer.photo, "thumb")}
            size="md"
          />
          <span className="flex flex-1 flex-col">
            {course.trainer.slug ? (
              <Link href={`/${course.trainer.slug}`} className="font-bold underline">
                {course.trainer.name}
              </Link>
            ) : (
              <span className="inline-flex items-center gap-1 font-bold">
                <SealCheck aria-hidden size={20} weight="fill" className="text-hibiscus" />
                {course.trainer.name}
              </span>
            )}
            {course.trainer.trained && (
              <span className="text-small text-prune-doux">{t("trained")}</span>
            )}
          </span>
        </div>
      </section>

      {course.description && (
        <section aria-labelledby="course-about" className="flex flex-col gap-3">
          <h2 id="course-about" className="text-title font-bold">
            {t("about")}
          </h2>
          <p className="whitespace-pre-line">{course.description}</p>
        </section>
      )}

      <section aria-labelledby="course-program" className="flex flex-col gap-4">
        <h2 id="course-program" className="text-title font-bold">
          {t("program")}
        </h2>
        <ol className="flex flex-col gap-4">
          {course.modules.map((module, index) => (
            <li key={module.id} className="border-trait bg-carte rounded-card border p-4">
              <h3 className="text-lead font-bold">
                {t("module", { number: index + 1, title: module.title })}
              </h3>
              <ol className="mt-2 flex flex-col">
                {module.lessons.map((lesson) => {
                  const open = canWatch || lesson.is_preview;
                  const content = (
                    <>
                      <span aria-hidden className="text-hibiscus shrink-0">
                        {lesson.done ? (
                          <CheckCircle size={24} weight="fill" className="text-feuille" />
                        ) : open ? (
                          <PlayCircle size={24} weight="duotone" />
                        ) : (
                          <LockSimple size={24} weight="duotone" className="text-prune-doux" />
                        )}
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="font-bold">{lesson.title}</span>
                        <span className="text-small text-prune-doux">
                          <Duration seconds={lesson.duration_seconds} />
                          {lesson.done && `, ${t("watched")}`}
                          {!canWatch && lesson.is_preview && `, ${t("preview")}`}
                          {!open && `, ${t("locked")}`}
                        </span>
                      </span>
                    </>
                  );
                  return (
                    <li key={lesson.id}>
                      {open ? (
                        <Link
                          href={`/academie/${course.slug}/lecon/${lesson.id}`}
                          className="hover:bg-poudre flex min-h-14 items-center gap-3 rounded-xl px-2 py-2"
                        >
                          {content}
                        </Link>
                      ) : (
                        <div className="flex min-h-14 items-center gap-3 px-2 py-2">{content}</div>
                      )}
                    </li>
                  );
                })}
              </ol>
              {module.questions_count > 0 && (
                <p className="text-small text-prune-doux mt-2 flex items-center gap-2 px-2">
                  <Exam aria-hidden size={20} />
                  {module.quiz_passed
                    ? t("quizPassed")
                    : t("quiz", { count: module.questions_count })}
                </p>
              )}
            </li>
          ))}
        </ol>
      </section>
    </article>
  );
}
