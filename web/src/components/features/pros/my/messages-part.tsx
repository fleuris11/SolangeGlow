"use client";

import { ArrowDown, ArrowUp, FloppyDisk, MoonStars, Plus, Trash } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  getAwayMessage,
  getQuickReplies,
  saveAwayMessage,
  saveQuickReplies,
} from "@/lib/api/messaging";

import { fieldClass, SectionFrame } from "./section-frame";

function QuickReplies() {
  const query = useQuery({ queryKey: ["quick-replies"], queryFn: getQuickReplies });
  if (query.isPending) return <Skeleton className="rounded-card h-32" />;
  return <QuickRepliesForm initial={query.data?.texts ?? []} />;
}

function QuickRepliesForm({ initial }: { initial: string[] }) {
  const t = useTranslations("pros.my.messages");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [texts, setTexts] = useState<string[]>(initial);
  const [draft, setDraft] = useState("");

  const move = (index: number, step: number) => {
    const next = [...texts];
    const [item] = next.splice(index, 1);
    if (item !== undefined) next.splice(index + step, 0, item);
    setTexts(next);
  };

  const save = async (values: string[]) => {
    try {
      const saved = await saveQuickReplies(values);
      queryClient.setQueryData(["quick-replies"], saved);
      toast(t("saved"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <section className="flex flex-col gap-3" aria-labelledby="quick-title">
      <h2 id="quick-title" className="text-title font-bold">
        {t("quickTitle")}
      </h2>
      <p className="text-small text-prune-doux">{t("quickHelp")}</p>
      <ul className="flex flex-col gap-2">
        {texts.map((text, index) => (
          <li
            key={`${index}-${text}`}
            className="border-trait rounded-card flex items-center gap-2 border p-3"
          >
            <p className="flex-1">{text}</p>
            <button
              type="button"
              aria-label={t("up", { text })}
              disabled={index === 0}
              onClick={() => move(index, -1)}
              className="hover:bg-poudre inline-flex size-12 items-center justify-center rounded-full disabled:opacity-40"
            >
              <ArrowUp aria-hidden size={20} weight="bold" />
            </button>
            <button
              type="button"
              aria-label={t("down", { text })}
              disabled={index === texts.length - 1}
              onClick={() => move(index, 1)}
              className="hover:bg-poudre inline-flex size-12 items-center justify-center rounded-full disabled:opacity-40"
            >
              <ArrowDown aria-hidden size={20} weight="bold" />
            </button>
            <button
              type="button"
              aria-label={t("remove", { text })}
              onClick={() => setTexts(texts.filter((_, i) => i !== index))}
              className="hover:bg-poudre text-alerte inline-flex size-12 items-center justify-center rounded-full"
            >
              <Trash aria-hidden size={20} weight="bold" />
            </button>
          </li>
        ))}
      </ul>
      <label htmlFor="quick-new" className="font-bold">
        {t("newReply")}
      </label>
      <textarea
        id="quick-new"
        rows={2}
        maxLength={500}
        value={draft}
        placeholder={t("placeholder")}
        onChange={(event) => setDraft(event.target.value)}
        className={fieldClass}
      />
      <Button
        variant="secondary"
        disabled={!draft.trim()}
        onClick={() => {
          setTexts([...texts, draft.trim()]);
          setDraft("");
        }}
      >
        <Plus aria-hidden size={20} weight="bold" />
        {t("add")}
      </Button>
      <Button onClick={() => void save(texts)}>
        <FloppyDisk aria-hidden size={20} weight="bold" />
        {t("saveReplies")}
      </Button>
    </section>
  );
}

function AwayMessage() {
  const query = useQuery({ queryKey: ["away-message"], queryFn: getAwayMessage });
  if (query.isPending) return <Skeleton className="rounded-card h-32" />;
  return <AwayMessageForm initial={query.data ?? { enabled: false, text: "" }} />;
}

function AwayMessageForm({ initial }: { initial: { enabled: boolean; text: string } }) {
  const t = useTranslations("pros.my.messages");
  const toast = useToast();
  const [enabled, setEnabled] = useState(initial.enabled);
  const [text, setText] = useState(initial.text);

  const save = async () => {
    try {
      await saveAwayMessage({ enabled, text });
      toast(t("saved"), "success");
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    }
  };

  return (
    <section className="flex flex-col gap-3" aria-labelledby="away-title">
      <h2 id="away-title" className="text-title font-bold">
        {t("awayTitle")}
      </h2>
      <SwitchRow
        icon={<MoonStars size={28} weight="duotone" />}
        label={t("awayLabel")}
        description={t("awayHelp")}
        checked={enabled}
        onChange={setEnabled}
      />
      <label htmlFor="away-text" className="font-bold">
        {t("awayText")}
      </label>
      <textarea
        id="away-text"
        rows={3}
        maxLength={500}
        value={text}
        placeholder={t("awayPlaceholder")}
        onChange={(event) => setText(event.target.value)}
        className={fieldClass}
      />
      <Button onClick={() => void save()}>
        <FloppyDisk aria-hidden size={20} weight="bold" />
        {t("saveAway")}
      </Button>
    </section>
  );
}

/** Messages of the pro: saved answers and the automatic answer outside her hours. */
export function MessagesPart() {
  const t = useTranslations("pros.my.messages");
  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <div className="flex flex-col gap-10">
        <QuickReplies />
        <AwayMessage />
      </div>
    </SectionFrame>
  );
}
