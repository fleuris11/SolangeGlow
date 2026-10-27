import { Clock, GraduationCap, PlayCircle, SealCheck } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import type { CourseCard as Card } from "@/lib/api/academy";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { CoursePrice, Duration } from "./parts";

/** A course in a list: cover, trade, title, trainer, level, length, price. */
export function CourseCard({ course }: { course: Card }) {
  const t = useTranslations("academy.card");
  const tLevels = useTranslations("academy.levels");
  const cover = mediaSrc(course.cover, "medium", "thumb");
  return (
    <Link
      href={`/academie/${course.slug}`}
      className="group border-trait bg-carte rounded-card flex h-full flex-col overflow-hidden border"
    >
      <span className="bg-poudre text-hibiscus relative flex aspect-video items-center justify-center">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
          <img
            src={cover}
            alt=""
            loading="lazy"
            width={480}
            height={270}
            className="size-full object-cover"
          />
        ) : (
          <GraduationCap aria-hidden size={56} weight="duotone" />
        )}
      </span>
      <span className="flex flex-1 flex-col gap-2 p-4">
        {course.trade_name && (
          <span className="text-small text-prune-doux font-bold">{course.trade_name}</span>
        )}
        <span className="text-lead line-clamp-2 font-bold group-hover:underline">
          {course.title}
        </span>
        <span className="text-small text-prune-doux flex items-center gap-1">
          {course.trainer.platform && (
            <SealCheck aria-hidden size={18} weight="fill" className="text-hibiscus" />
          )}
          {t("by", { name: course.trainer.name })}
        </span>
        <span className="text-small text-prune-doux flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>{tLevels(course.level)}</span>
          <span className="inline-flex items-center gap-1">
            <PlayCircle aria-hidden size={18} />
            {t("lessons", { count: course.lessons_count })}
          </span>
          {course.duration_seconds > 0 && (
            <span className="inline-flex items-center gap-1">
              <Clock aria-hidden size={18} />
              <Duration seconds={course.duration_seconds} />
            </span>
          )}
        </span>
        <span className="mt-auto pt-1">
          <CoursePrice course={course} />
        </span>
      </span>
    </Link>
  );
}
