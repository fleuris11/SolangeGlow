"use client";

import { Camera, Plus, Scales, Trash } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Avatar } from "@/components/ui/avatar";
import { Button, buttonClasses } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError, type Schemas } from "@/lib/api/client";
import {
  createPoll,
  deletePoll,
  getPoll,
  getPolls,
  uploadGamePhoto,
  votePoll,
  type Poll,
} from "@/lib/api/games";
import { cn } from "@/lib/cn";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

function useLeft() {
  const t = useTranslations("games.polls");
  return (poll: Poll) => {
    const minutes = Math.round((new Date(poll.ends_at).getTime() - Date.now()) / 60_000);
    if (poll.ended || minutes <= 0) return t("ended");
    if (minutes < 60) return t("leftMinutes", { count: minutes });
    return t("leftHours", { count: Math.round(minutes / 60) });
  };
}

/** One question: two photos side by side; tap one to vote, then the shares. */
export function PollCard({ poll, onChange }: { poll: Poll; onChange?: (poll: Poll) => void }) {
  const t = useTranslations("games.polls");
  const toast = useToast();
  const left = useLeft();
  const [busy, setBusy] = useState(false);
  const canVote = !poll.mine && !poll.my_vote && !poll.ended;

  const vote = async (choice: "a" | "b") => {
    setBusy(true);
    try {
      onChange?.(await votePoll(poll.id, choice));
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  const side = (choice: "a" | "b") => {
    const photo = choice === "a" ? poll.photo_a : poll.photo_b;
    const label = (choice === "a" ? poll.label_a : poll.label_b) || choice.toUpperCase();
    const share = poll.result ? poll.result[choice] : null;
    const picked = poll.my_vote === choice;
    const content = (
      <>
        {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
        <img
          src={mediaSrc(photo, "medium", "thumb")}
          alt={label}
          loading="lazy"
          className="rounded-photo bg-poudre aspect-[3/4] w-full object-cover"
        />
        <span className="flex items-center justify-between gap-2 font-bold">
          <span className="truncate">{label}</span>
          {share !== null && <span>{t("share", { value: share })}</span>}
        </span>
        {share !== null && (
          <span className="bg-poudre h-2 overflow-hidden rounded-full" aria-hidden>
            <span
              className={cn("block h-full rounded-full", picked ? "bg-hibiscus" : "bg-prune-doux")}
              style={{ width: `${share}%` }}
            />
          </span>
        )}
        {picked && <span className="text-small text-hibiscus font-bold">{t("myVote")}</span>}
      </>
    );
    return canVote ? (
      <button
        type="button"
        disabled={busy}
        onClick={() => vote(choice)}
        aria-label={t("voteFor", { label })}
        className="rounded-card hover:border-hibiscus flex flex-col gap-2 border-2 border-transparent p-1 text-left"
      >
        {content}
      </button>
    ) : (
      <div className="flex flex-col gap-2 p-1">{content}</div>
    );
  };

  return (
    <article className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4">
      <header className="flex items-center gap-3">
        <Avatar name={poll.author.name} src={mediaSrc(poll.author.photo, "thumb")} size="sm" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-bold">{poll.author.name}</span>
          <span className="text-small text-prune-doux">{left(poll)}</span>
        </span>
      </header>
      {poll.caption && <p className="text-lead font-bold">{poll.caption}</p>}
      <div className="grid grid-cols-2 gap-2">
        {side("a")}
        {side("b")}
      </div>
      <p className="text-small text-prune-doux">
        {poll.result
          ? t("votes", { count: poll.result.total })
          : canVote
            ? t("tapToVote")
            : t("hidden")}
      </p>
    </article>
  );
}

/** « Help me choose »: the questions to vote on, and mine. */
export function PollsScreen() {
  const t = useTranslations("games.polls");
  const client = useQueryClient();
  const [scope, setScope] = useState<"vote" | "mine">("vote");
  const query = useQuery({ queryKey: ["glow-polls", scope], queryFn: () => getPolls(scope) });
  const replace = (fresh: Poll) =>
    client.setQueryData<Schemas["PollList"]>(["glow-polls", scope], (old) =>
      old ? { ...old, results: old.results.map((p) => (p.id === fresh.id ? fresh : p)) } : old,
    );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={`${t("title")}. ${t("help")}`} />
      </div>
      <p className="text-prune-doux">{t("help")}</p>
      <Link href="/choisir/nouveau" className={buttonClasses({ size: "lg", fullWidth: true })}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("ask")}
      </Link>
      <div role="tablist" className="bg-poudre grid grid-cols-2 gap-1 rounded-full p-1">
        {(["vote", "mine"] as const).map((value) => (
          <button
            key={value}
            role="tab"
            type="button"
            aria-selected={scope === value}
            onClick={() => setScope(value)}
            className={cn(
              "min-h-12 rounded-full font-bold",
              scope === value ? "bg-carte text-prune" : "text-prune-doux",
            )}
          >
            {t(value === "vote" ? "tabVote" : "tabMine")}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="flex flex-col gap-4">
        {query.isPending && <Skeleton className="rounded-card h-96" />}
        {query.data?.results.length === 0 && (
          <EmptyState
            icon={<Scales size={48} weight="duotone" />}
            title={scope === "vote" ? t("noneToVote") : t("noneMine")}
            description={t("noneHelp")}
          />
        )}
        {query.data?.results.map((poll) => (
          <PollCard key={poll.id} poll={poll} onChange={replace} />
        ))}
      </div>
    </div>
  );
}

/** One question opened from a link or a notification (its result for the author). */
export function PollDetail({ id }: { id: string }) {
  const t = useTranslations("games.polls");
  const router = useRouter();
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["glow-poll", id], queryFn: () => getPoll(id) });
  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  if (!query.data) {
    return (
      <p role="alert" className="font-bold">
        {query.error instanceof ApiError ? query.error.message : t("error")}
      </p>
    );
  }
  const remove = async () => {
    await deletePoll(id);
    toast(t("deleted"), "success");
    client.invalidateQueries({ queryKey: ["glow-polls"] });
    router.push("/choisir");
  };
  return (
    <div className="flex flex-col gap-4">
      <PollCard
        poll={query.data}
        onChange={(fresh) => client.setQueryData(["glow-poll", id], fresh)}
      />
      {query.data.mine && (
        <Button variant="quiet" onClick={remove}>
          <Trash aria-hidden size={22} />
          {t("delete")}
        </Button>
      )}
      <Link href="/choisir" className={buttonClasses({ variant: "secondary" })}>
        {t("all")}
      </Link>
    </div>
  );
}

type Picked = { id: string; preview: string } | null;

function PhotoPick({
  label,
  value,
  onPicked,
}: {
  label: string;
  value: Picked;
  onPicked: (value: Picked) => void;
}) {
  const t = useTranslations("games.polls");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const pick = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    try {
      const media = await uploadGamePhoto(file, "poll_photo");
      onPicked({ id: media.id, preview: URL.createObjectURL(file) });
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  return (
    <label className="border-trait bg-poudre rounded-card flex aspect-[3/4] cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden border-2 border-dashed text-center">
      {value ? (
        // eslint-disable-next-line @next/next/no-img-element -- local preview
        <img src={value.preview} alt={label} className="size-full object-cover" />
      ) : (
        <>
          <Camera aria-hidden size={36} weight="duotone" className="text-hibiscus" />
          <span className="font-bold">{busy ? t("sending") : label}</span>
        </>
      )}
      <input
        type="file"
        accept="image/*"
        className="sr-only"
        aria-label={label}
        onChange={(event) => pick(event.target.files?.[0])}
      />
    </label>
  );
}

/** Ask the community: two photos, a question, how long the vote lasts. */
export function PollCreate() {
  const t = useTranslations("games.polls");
  const toast = useToast();
  const router = useRouter();
  const options = useQuery({ queryKey: ["glow-polls", "vote"], queryFn: () => getPolls("vote") });
  const durations = options.data?.durations ?? [24];
  const [a, setA] = useState<Picked>(null);
  const [b, setB] = useState<Picked>(null);
  const [caption, setCaption] = useState("");
  const [labelA, setLabelA] = useState("");
  const [labelB, setLabelB] = useState("");
  const [hours, setHours] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const chosen = hours ?? (durations.includes(24) ? 24 : (durations[0] ?? 24));

  const publish = async () => {
    if (!a || !b) return;
    setBusy(true);
    try {
      const poll = await createPoll({
        caption,
        photo_a: a.id,
        photo_b: b.id,
        label_a: labelA,
        label_b: labelB,
        hours: chosen,
      });
      toast(t("published"), "success");
      router.push(`/choisir/${poll.id}`);
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-headline font-bold">{t("newTitle")}</h1>
      <div className="grid grid-cols-2 gap-3">
        <PhotoPick label={t("photoA")} value={a} onPicked={setA} />
        <PhotoPick label={t("photoB")} value={b} onPicked={setB} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Input
          label={t("labelA")}
          value={labelA}
          maxLength={40}
          onChange={(e) => setLabelA(e.target.value)}
        />
        <Input
          label={t("labelB")}
          value={labelB}
          maxLength={40}
          onChange={(e) => setLabelB(e.target.value)}
        />
      </div>
      <Input
        label={t("caption")}
        hint={t("captionHint")}
        value={caption}
        maxLength={140}
        onChange={(event) => setCaption(event.target.value)}
      />
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("duration")}</legend>
        <div className="flex flex-wrap gap-2">
          {durations.map((value) => (
            <Chip key={value} selected={chosen === value} onClick={() => setHours(value)}>
              {t("hours", { count: value })}
            </Chip>
          ))}
        </div>
      </fieldset>
      <Button size="lg" fullWidth disabled={!a || !b || busy} onClick={publish}>
        {t("publish")}
      </Button>
    </div>
  );
}
