"use client";

import {
  Bell,
  CalendarStar,
  CheckSquare,
  Moon,
  PencilSimple,
  Plus,
  Square,
  Sun,
  Trash,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getRoutine, saveReminders, saveRoutine, tickStep, type Routine } from "@/lib/api/games";
import { cn } from "@/lib/cn";

type Moment = "morning" | "evening";
const SUGGESTIONS: Record<Moment, string[]> = {
  morning: ["cleanse", "serum", "moisturise", "sunscreen", "lips"],
  evening: ["removeMakeup", "cleanse", "shea", "scarf", "nightCream"],
};

/** « My routine »: steps to tick in the morning and in the evening, with reminders. */
export function RoutineScreen() {
  const t = useTranslations("games.routine");
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["glow-routine"], queryFn: getRoutine });
  const [moment, setMoment] = useState<Moment>(() =>
    new Date().getHours() >= 15 ? "evening" : "morning",
  );
  const [editing, setEditing] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const routine = query.data;
  if (!routine) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const update = (fresh: Routine) => client.setQueryData(["glow-routine"], fresh);
  const fail = (failure: unknown) =>
    toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
  const steps = routine[moment];
  const done = steps.filter((step) => step.done).length;

  const tick = async (id: string, value: boolean) => {
    try {
      const fresh = await tickStep(id, value);
      update(fresh);
      const after = fresh[moment];
      if (value && after.length > 0 && after.every((step) => step.done)) {
        toast(t("complete"), "success");
        client.invalidateQueries({ queryKey: ["glow-me"] });
      }
    } catch (failure) {
      fail(failure);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={[t("title"), ...steps.map((s) => s.label)].join(". ")} />
      </div>
      <div role="tablist" className="bg-poudre grid grid-cols-2 gap-1 rounded-full p-1">
        {(["morning", "evening"] as const).map((value) => (
          <button
            key={value}
            role="tab"
            type="button"
            aria-selected={moment === value}
            onClick={() => setMoment(value)}
            className={cn(
              "inline-flex min-h-12 items-center justify-center gap-2 rounded-full font-bold",
              moment === value ? "bg-carte text-prune" : "text-prune-doux",
            )}
          >
            {value === "morning" ? (
              <Sun aria-hidden size={22} weight="duotone" />
            ) : (
              <Moon aria-hidden size={22} weight="duotone" />
            )}
            {t(value)}
          </button>
        ))}
      </div>

      {editing ? (
        <StepsEditor
          routine={routine}
          onSaved={(fresh) => {
            update(fresh);
            setEditing(false);
          }}
          onError={fail}
        />
      ) : (
        <section role="tabpanel" className="flex flex-col gap-3">
          {steps.length === 0 ? (
            <p className="text-prune-doux">{t("empty")}</p>
          ) : (
            <>
              <p className="font-bold" aria-live="polite">
                {t("progress", { done, total: steps.length })}
              </p>
              <ul className="flex flex-col gap-2">
                {steps.map((step) => (
                  <li key={step.id}>
                    <button
                      type="button"
                      role="checkbox"
                      aria-checked={step.done}
                      onClick={() => tick(step.id, !step.done)}
                      className={cn(
                        "rounded-card text-lead flex min-h-16 w-full items-center gap-3 border-2 px-4 text-left font-bold",
                        step.done ? "border-feuille bg-carte" : "border-trait bg-carte",
                      )}
                    >
                      {step.done ? (
                        <CheckSquare aria-hidden size={32} weight="fill" className="text-feuille" />
                      ) : (
                        <Square aria-hidden size={32} className="text-prune-doux" />
                      )}
                      <span className={cn("flex-1", step.done && "line-through")}>
                        {step.label}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
          <Button variant="secondary" onClick={() => setEditing(true)}>
            <PencilSimple aria-hidden size={22} />
            {steps.length === 0 ? t("create") : t("edit")}
          </Button>
        </section>
      )}

      <Reminders routine={routine} onSaved={update} onError={fail} />
    </div>
  );
}

function StepsEditor({
  routine,
  onSaved,
  onError,
}: {
  routine: Routine;
  onSaved: (fresh: Routine) => void;
  onError: (failure: unknown) => void;
}) {
  const t = useTranslations("games.routine");
  const tSuggest = useTranslations("games.routine.suggestions");
  const [lists, setLists] = useState<Record<Moment, string[]>>({
    morning: routine.morning.map((s) => s.label),
    evening: routine.evening.map((s) => s.label),
  });
  const [busy, setBusy] = useState(false);
  const change = (moment: Moment, index: number, value: string) =>
    setLists((old) => ({ ...old, [moment]: old[moment].map((v, i) => (i === index ? value : v)) }));
  const add = (moment: Moment, value = "") =>
    setLists((old) =>
      old[moment].length >= routine.max_steps ? old : { ...old, [moment]: [...old[moment], value] },
    );
  const remove = (moment: Moment, index: number) =>
    setLists((old) => ({ ...old, [moment]: old[moment].filter((_, i) => i !== index) }));
  const save = async () => {
    setBusy(true);
    try {
      onSaved(
        await saveRoutine({
          morning: lists.morning.filter((v) => v.trim()),
          evening: lists.evening.filter((v) => v.trim()),
        }),
      );
    } catch (failure) {
      onError(failure);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flex flex-col gap-6">
      {(["morning", "evening"] as const).map((moment) => (
        <fieldset key={moment} className="flex flex-col gap-3">
          <legend className="text-title mb-2 font-bold">{t(moment)}</legend>
          {lists[moment].map((value, index) => (
            <div key={index} className="flex items-end gap-2">
              <Input
                className="flex-1"
                label={t("step", { number: index + 1 })}
                value={value}
                maxLength={60}
                onChange={(event) => change(moment, index, event.target.value)}
              />
              <button
                type="button"
                onClick={() => remove(moment, index)}
                aria-label={t("remove", { number: index + 1 })}
                className="hover:bg-poudre inline-flex size-12 items-center justify-center rounded-full"
              >
                <Trash aria-hidden size={22} />
              </button>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS[moment].map((key) => (
              <Chip
                key={key}
                icon={<Plus aria-hidden size={16} />}
                onClick={() => add(moment, tSuggest(key as "cleanse"))}
              >
                {tSuggest(key as "cleanse")}
              </Chip>
            ))}
          </div>
          <Button variant="quiet" onClick={() => add(moment)} className="self-start">
            <Plus aria-hidden size={20} />
            {t("addStep")}
          </Button>
        </fieldset>
      ))}
      <Button size="lg" fullWidth onClick={save} disabled={busy}>
        {t("save")}
      </Button>
    </section>
  );
}

function Reminders({
  routine,
  onSaved,
  onError,
}: {
  routine: Routine;
  onSaved: (fresh: Routine) => void;
  onError: (failure: unknown) => void;
}) {
  const t = useTranslations("games.routine");
  const send = async (changes: Partial<Routine>) => {
    try {
      const next = { ...routine, ...changes };
      onSaved(
        await saveReminders({
          routine_reminders: next.routine_reminders,
          morning_at: next.morning_at,
          evening_at: next.evening_at,
          celebration_reminders: next.celebration_reminders,
        }),
      );
    } catch (failure) {
      onError(failure);
    }
  };
  return (
    <section aria-labelledby="reminders-title" className="flex flex-col gap-3">
      <h2 id="reminders-title" className="text-title font-bold">
        {t("reminders")}
      </h2>
      <SwitchRow
        icon={<Bell size={24} weight="duotone" />}
        label={t("remindMe")}
        description={t("remindMeHelp")}
        checked={routine.routine_reminders}
        onChange={(value) => send({ routine_reminders: value })}
      />
      {routine.routine_reminders && (
        <div className="grid grid-cols-2 gap-3">
          <Input
            type="time"
            label={t("morningAt")}
            value={routine.morning_at}
            onChange={(event) => event.target.value && send({ morning_at: event.target.value })}
          />
          <Input
            type="time"
            label={t("eveningAt")}
            value={routine.evening_at}
            onChange={(event) => event.target.value && send({ evening_at: event.target.value })}
          />
        </div>
      )}
      <SwitchRow
        icon={<CalendarStar size={24} weight="duotone" />}
        label={t("celebrations")}
        description={t("celebrationsHelp")}
        checked={routine.celebration_reminders}
        onChange={(value) => send({ celebration_reminders: value })}
      />
    </section>
  );
}
