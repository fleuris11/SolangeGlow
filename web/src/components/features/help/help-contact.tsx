"use client";

import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { sendTicket, suggestAnswers, type FaqItem } from "@/lib/api/help";
import { useMe } from "@/lib/auth/use-me";

import { RichText } from "./rich-text";

type Step = "ask" | "answers" | "write" | "sent";

const fieldClass =
  "rounded-field bg-poudre focus:border-hibiscus text-body border-2 border-transparent p-3 outline-none";

/**
 * « Ask your question »: the answers of the FAQ come first (the assistant of the help
 * center); when they do not help, the question goes to the team as a ticket.
 */
export function HelpContact({
  searchIcon,
  sendIcon,
}: {
  searchIcon: ReactNode;
  sendIcon: ReactNode;
}) {
  const t = useTranslations("help.contact");
  const { data: me } = useMe();
  const questionId = useId();
  const [step, setStep] = useState<Step>("ask");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [found, setFound] = useState<FaqItem[]>([]);
  const [contact, setContact] = useState({ name: "", email: "", phone: "" });
  const [reference, setReference] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (question.trim().length < 3) return;
    setBusy(true);
    setError(null);
    try {
      const result = await suggestAnswers(question);
      setAnswer(result.answer ?? null);
      setFound(result.faq);
      setStep(result.answer || result.faq.length > 0 ? "answers" : "write");
    } catch {
      setStep("write");
    } finally {
      setBusy(false);
    }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const ticket = await sendTicket({ message: question, topic: "", ...contact });
      setReference(ticket.reference);
      setStep("sent");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure : new ApiError(0));
    } finally {
      setBusy(false);
    }
  }

  function restart() {
    setQuestion("");
    setFound([]);
    setAnswer(null);
    setStep("ask");
  }

  if (step === "sent") {
    return (
      <section aria-live="polite" className="bg-poudre rounded-card flex flex-col gap-3 p-4">
        <h2 className="text-title font-bold">{t("sentTitle")}</h2>
        <p>{t("sentText", { reference })}</p>
        <Button variant="secondary" onClick={restart} className="self-start">
          {t("another")}
        </Button>
      </section>
    );
  }

  return (
    <section aria-labelledby={`${questionId}-title`} className="flex flex-col gap-4">
      <h2 id={`${questionId}-title`} className="text-title font-bold">
        {t("title")}
      </h2>
      <form onSubmit={search} className="flex flex-col gap-3">
        <label htmlFor={questionId} className="font-bold">
          {t("question")}
        </label>
        <textarea
          id={questionId}
          value={question}
          rows={3}
          maxLength={3000}
          required
          minLength={3}
          placeholder={t("placeholder")}
          onChange={(event) => {
            setQuestion(event.target.value);
            if (step !== "ask") setStep("ask");
          }}
          className={fieldClass}
        />
        {step === "ask" && (
          <Button type="submit" icon={searchIcon} disabled={busy} className="self-start">
            {t("search")}
          </Button>
        )}
      </form>

      {step === "answers" && (
        <div aria-live="polite" className="flex flex-col gap-3">
          <p className="font-bold">{t("found")}</p>
          {answer && (
            <div className="border-trait rounded-card bg-carte border p-4">
              <RichText text={answer} />
            </div>
          )}
          {found.map((item) => (
            <details key={item.id} className="border-trait rounded-card bg-carte border px-4">
              <summary className="flex min-h-14 cursor-pointer items-center py-3 font-bold">
                {item.question}
              </summary>
              <div className="pb-4">
                <RichText text={item.answer} />
              </div>
            </details>
          ))}
          <div className="flex flex-wrap gap-3">
            <Button onClick={restart}>{t("solved")}</Button>
            <Button variant="secondary" onClick={() => setStep("write")}>
              {t("notSolved")}
            </Button>
          </div>
        </div>
      )}

      {step === "write" && (
        <form onSubmit={send} className="flex flex-col gap-4" aria-live="polite">
          <p>{t("writeIntro")}</p>
          {!me && (
            <>
              <Input
                label={t("name")}
                autoComplete="name"
                required
                value={contact.name}
                maxLength={120}
                error={error?.fieldMessage("name")}
                onChange={(event) => setContact({ ...contact, name: event.target.value })}
              />
              <Input
                label={t("email")}
                type="email"
                autoComplete="email"
                hint={t("reachHint")}
                value={contact.email}
                error={error?.fieldMessage("email")}
                onChange={(event) => setContact({ ...contact, email: event.target.value })}
              />
              <Input
                label={t("phone")}
                type="tel"
                autoComplete="tel"
                value={contact.phone}
                maxLength={30}
                error={error?.fieldMessage("phone")}
                onChange={(event) => setContact({ ...contact, phone: event.target.value })}
              />
            </>
          )}
          {error && !error.body.fields && (
            <p role="alert" className="text-alerte font-bold">
              {error.status ? error.message : t("error")}
            </p>
          )}
          <Button type="submit" icon={sendIcon} disabled={busy} className="self-start">
            {t("send")}
          </Button>
        </form>
      )}
    </section>
  );
}
