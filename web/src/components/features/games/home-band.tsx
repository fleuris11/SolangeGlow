import {
  CalendarStar,
  Camera,
  Disc,
  Fire,
  Lightbulb,
  Scales,
  Trophy,
} from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { GlowToday } from "@/lib/api/games";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

import { CheckIn } from "./check-in";
import { LevelBadge } from "./glow-bits";

function Tile({
  href,
  icon,
  title,
  text,
}: {
  href: string;
  icon: ReactNode;
  title: string;
  text: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="border-trait bg-lait rounded-card flex min-h-24 flex-col gap-1 border p-3"
      >
        <span aria-hidden className="text-hibiscus">
          {icon}
        </span>
        <span className="font-bold">{title}</span>
        <span className="text-small text-prune-doux">{text}</span>
      </Link>
    </li>
  );
}

/** « Your Glow day » on the home page: streak, points, the games of the day. Rendered on
 * the server; only the daily visit is a (tiny) island. */
export function GlowTodayBand({ today }: { today: GlowToday }) {
  const t = useTranslations("games.today");
  if (!today.signed_in || !today.games_open || !today.summary || !today.streak) return null;
  const quiz = today.quiz;
  return (
    <section
      aria-labelledby="glow-today-title"
      className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 id="glow-today-title" className="text-title font-bold">
          {t("title")}
        </h2>
        <Link href="/points" className="flex flex-col items-end gap-1">
          <span className="font-bold">{t("points", { count: today.summary.balance })}</span>
          <LevelBadge level={today.summary.level} />
        </Link>
      </div>
      <CheckIn
        streak={today.streak.streak}
        done={today.streak.today_done}
        flame={<Fire aria-hidden size={28} weight="fill" className="text-hibiscus" />}
      />
      <ul className="grid grid-cols-2 gap-2">
        <Tile
          href="/quiz"
          icon={<Lightbulb size={28} weight="duotone" />}
          title={t("quiz")}
          text={
            quiz
              ? quiz.answered >= quiz.total
                ? t("quizDone", { score: quiz.score, total: quiz.total })
                : t("quizOpen", { total: quiz.total })
              : t("quizNone")
          }
        />
        <Tile
          href="/roue"
          icon={<Disc size={28} weight="duotone" />}
          title={t("wheel")}
          text={today.wheel?.can_spin ? t("wheelOpen") : t("wheelDone")}
        />
        <Tile
          href="/defi"
          icon={<Camera size={28} weight="duotone" />}
          title={t("challenge")}
          text={today.challenge ? today.challenge.theme : t("challengeNone")}
        />
        <Tile
          href="/choisir"
          icon={<Scales size={28} weight="duotone" />}
          title={t("polls")}
          text={today.poll ? t("pollOpen") : t("pollNone")}
        />
      </ul>
      {today.celebration && (
        <Link href="/fetes" className="inline-flex items-center gap-2 font-bold">
          <CalendarStar aria-hidden size={24} weight="duotone" className="text-hibiscus" />
          {today.celebration.days_left === 0
            ? t("celebrationToday", { name: today.celebration.name })
            : t("celebration", {
                name: today.celebration.name,
                count: today.celebration.days_left,
              })}
        </Link>
      )}
    </section>
  );
}

/** Last week's photo challenge winner, shown on the home page to everyone. */
export function WinnerBand({ featured }: { featured: GlowToday["featured"] }) {
  const t = useTranslations("games.challenge");
  if (!featured) return null;
  return (
    <section aria-labelledby="home-winner-title">
      <Link
        href="/defi"
        className="border-or bg-carte rounded-card flex items-center gap-4 border-2 p-4"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
        <img
          src={mediaSrc(featured.winner.photo, "thumb", "medium")}
          alt=""
          loading="lazy"
          width={96}
          height={96}
          className="petal bg-poudre size-24 shrink-0 object-cover"
        />
        <span className="flex min-w-0 flex-col gap-1">
          <span className="text-small inline-flex items-center gap-1 font-bold">
            <Trophy aria-hidden size={18} weight="fill" className="text-or" />
            {t("winnerLabel")}
          </span>
          <span id="home-winner-title" className="text-lead font-bold">
            {featured.winner.author.name}
          </span>
          <span className="text-small text-prune-doux">
            {t("winnerOf", { theme: featured.theme, count: featured.winner.votes })}
          </span>
        </span>
      </Link>
    </section>
  );
}
