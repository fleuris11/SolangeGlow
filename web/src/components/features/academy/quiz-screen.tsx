"use client";

import { ArrowLeft, CheckCircle, Exam, XCircle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button, buttonClasses } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { answerQuiz, getQuiz, type QuizResult } from "@/lib/api/academy";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

/** The quiz at the end of a module: one answer per question, the right ones shown after. */
export function QuizScreen({ slug, moduleId }: { slug: string; moduleId: string }) {
  const t = useTranslations("academy.quiz");
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["academy-quiz", moduleId],
    queryFn: () => getQuiz(moduleId),
  });
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const back = `/academie/${slug}`;

  if (query.isPending) return <Skeleton className="h-80 rounded-2xl" />;
  if (!query.data) {
    return (
      <div className="flex flex-col gap-4">
        <p role="alert" className="font-bold">
          {query.error instanceof ApiError ? query.error.message : t("error")}
        </p>
        <Link href={back} className={buttonClasses({ variant: "secondary" })}>
          {t("back")}
        </Link>
      </div>
    );
  }
  const quiz = query.data;
  const complete = quiz.questions.every((question) => question.id in answers);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const answer = await answerQuiz(
        moduleId,
        quiz.questions.map((question) => answers[question.id] ?? 0),
      );
      setResult(answer);
      void queryClient.invalidateQueries({ queryKey: ["academy-quiz", moduleId] });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const verdict = (questionId: string) => result?.results.find((r) => r.question === questionId);

  return (
    <article className="flex flex-col gap-6">
      <Link
        href={back}
        className="text-prune-doux inline-flex min-h-12 items-center gap-2 self-start font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {t("back")}
      </Link>
      <header className="flex flex-col gap-2">
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
            <Exam aria-hidden size={30} weight="duotone" className="text-hibiscus" />
            {t("title", { module: quiz.module_title })}
          </h1>
          <SpeakButton text={t("help", { percent: quiz.pass_percent })} />
        </div>
        <p>{t("help", { percent: quiz.pass_percent })}</p>
      </header>

      {!quiz.unlocked ? (
        <div className="flex flex-col gap-4">
          <p className="bg-poudre rounded-2xl p-3 font-bold">{t("locked")}</p>
          <Link href={back} className={buttonClasses({ size: "lg", fullWidth: true })}>
            {t("watchFirst")}
          </Link>
        </div>
      ) : (
        <>
          {result && (
            <div
              role="status"
              className={cn(
                "flex flex-col items-center gap-3 rounded-2xl p-4 text-center",
                result.passed ? "bg-poudre" : "border-alerte border-2",
              )}
            >
              {result.passed && <Bloom label={t("passedShort")} size={96} />}
              <p className="text-title font-bold">
                {result.passed
                  ? t("passed", { score: result.score_percent })
                  : t("failed", { score: result.score_percent, percent: result.pass_percent })}
              </p>
              {result.progress.certificate && <p>{t("certificate")}</p>}
            </div>
          )}
          <ol className="flex flex-col gap-5">
            {quiz.questions.map((question, index) => {
              const line = verdict(question.id);
              return (
                <li key={question.id}>
                  <div
                    role="radiogroup"
                    aria-labelledby={`question-${question.id}`}
                    className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-4"
                  >
                    <p id={`question-${question.id}`} className="text-lead mb-2 font-bold">
                      {index + 1}. {question.text}
                    </p>
                    {question.choices.map((choice, position) => {
                      const chosen = answers[question.id] === position;
                      const right = line && line.correct === position;
                      return (
                        <label
                          key={position}
                          className={cn(
                            "flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border-2 px-3",
                            chosen ? "border-hibiscus bg-poudre" : "border-trait",
                          )}
                        >
                          <input
                            type="radio"
                            name={`q-${question.id}`}
                            checked={chosen}
                            disabled={Boolean(result?.passed)}
                            onChange={() => {
                              setAnswers({ ...answers, [question.id]: position });
                              if (result && !result.passed) setResult(null);
                            }}
                            className="accent-hibiscus size-6"
                          />
                          <span className="flex min-w-0 flex-1 flex-col py-2">
                            <span>{choice}</span>
                            {right && (
                              <span className="text-feuille text-small inline-flex items-center gap-1 font-bold">
                                <CheckCircle aria-hidden size={20} weight="fill" />
                                {t("right")}
                              </span>
                            )}
                          </span>
                        </label>
                      );
                    })}
                    {line && !line.right && (
                      <p className="text-alerte flex items-center gap-1 font-bold">
                        <XCircle aria-hidden size={22} weight="fill" />
                        {t("wrong")}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
          {error && (
            <p role="alert" className="text-alerte font-bold">
              {error}
            </p>
          )}
          {result?.passed ? (
            <Link href={back} className={buttonClasses({ size: "lg", fullWidth: true })}>
              {t("continue")}
            </Link>
          ) : (
            <Button size="lg" fullWidth disabled={!complete || busy} onClick={() => void submit()}>
              {result ? t("retry") : t("submit")}
            </Button>
          )}
        </>
      )}
    </article>
  );
}
