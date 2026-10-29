"use client";

import { CheckCircle, Lightbulb, XCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";
import { ApiError, type Schemas } from "@/lib/api/client";
import { answerQuiz, getQuiz, type DailyQuiz } from "@/lib/api/games";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, voiceSrc } from "@/lib/media";

type Answer = Schemas["DailyQuizAnswer"];

/** The beauty quiz of the day: one question at a time, a picture, audio, big answers. */
export function DailyQuizScreen() {
  const t = useTranslations("games.quiz");
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["glow-quiz"], queryFn: getQuiz });
  const [index, setIndex] = useState<number | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [chosen, setChosen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const quiz = query.data?.quiz;
  if (!quiz || quiz.questions.length === 0) {
    return (
      <EmptyState
        icon={<Lightbulb size={48} weight="duotone" />}
        title={t("none")}
        description={t("noneHelp")}
        action={
          <Link href="/points" className={buttonClasses({ variant: "secondary" })}>
            {t("back")}
          </Link>
        }
      />
    );
  }
  const firstOpen = quiz.questions.findIndex((q) => q.answered === null);
  const current = index ?? (firstOpen === -1 ? quiz.questions.length : firstOpen);
  const question = quiz.questions[current];
  if (!question) return <QuizDone quiz={quiz} />;
  const picture = mediaSrc(question.image, "medium", "large");
  const audio = voiceSrc(question.audio);

  const choose = async (choice: number) => {
    setBusy(true);
    setChosen(choice);
    try {
      setAnswer(await answerQuiz(question.id, choice));
    } catch (failure) {
      setChosen(null);
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  const next = async () => {
    await client.invalidateQueries({ queryKey: ["glow-quiz"] });
    client.invalidateQueries({ queryKey: ["glow-me"] });
    setAnswer(null);
    setChosen(null);
    setIndex(current + 1);
  };

  return (
    <div className="flex flex-col gap-5">
      <Stepper current={current + 1} total={quiz.questions.length} />
      {picture && (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img
          src={picture}
          alt=""
          className="rounded-photo bg-poudre aspect-[4/3] w-full object-cover"
        />
      )}
      <div className="flex items-start gap-2">
        <h1 className="text-title flex-1 font-bold">{question.text}</h1>
        <SpeakButton always text={[question.text, ...question.choices].join(". ")} />
      </div>
      {audio && (
        <audio controls src={audio} className="w-full" aria-label={t("listen")}>
          <track kind="captions" />
        </audio>
      )}
      <ul className="flex flex-col gap-3">
        {question.choices.map((choice, position) => {
          const value = position + 1;
          const right = answer && answer.answer === value;
          const wrong = answer && chosen === value && !answer.correct;
          return (
            <li key={choice}>
              <button
                type="button"
                disabled={busy || answer !== null}
                onClick={() => choose(value)}
                className={cn(
                  "rounded-card text-lead flex min-h-16 w-full items-center gap-3 border-2 px-5 text-left font-bold",
                  right
                    ? "border-feuille bg-carte"
                    : wrong
                      ? "border-alerte bg-carte"
                      : "border-trait bg-carte hover:border-hibiscus",
                )}
              >
                <span className="flex-1">{choice}</span>
                {right && (
                  <CheckCircle aria-hidden size={28} weight="fill" className="text-feuille" />
                )}
                {wrong && <XCircle aria-hidden size={28} weight="fill" className="text-alerte" />}
              </button>
            </li>
          );
        })}
      </ul>
      {answer && (
        <div aria-live="polite" className="bg-poudre rounded-card flex flex-col gap-2 p-4">
          <p className="text-lead font-bold">
            {answer.correct ? t("right", { points: answer.gained }) : t("wrong")}
          </p>
          {answer.explanation && <p>{answer.explanation}</p>}
        </div>
      )}
      {answer && (
        <Button size="lg" fullWidth onClick={next}>
          {current + 1 < quiz.questions.length ? t("next") : t("finish")}
        </Button>
      )}
    </div>
  );
}

function QuizDone({ quiz }: { quiz: DailyQuiz }) {
  const t = useTranslations("games.quiz");
  const total = quiz.questions.length;
  return (
    <div className="flex flex-col items-center gap-4 text-center">
      {quiz.score > 0 && <Bloom label={t("doneTitle")} />}
      <h1 className="font-display text-headline font-black">{t("doneTitle")}</h1>
      <p className="text-lead font-bold">
        {t("score", { score: quiz.score, total, points: quiz.score * quiz.points_per_answer })}
      </p>
      <p className="text-prune-doux">{t("tomorrow")}</p>
      <Link href="/points" className={buttonClasses({ size: "lg", fullWidth: true })}>
        {t("back")}
      </Link>
    </div>
  );
}
