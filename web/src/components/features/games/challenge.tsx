"use client";

import { Camera, Heart, Trophy } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Bloom } from "@/components/ui/bloom";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  enterChallenge,
  getChallenge,
  uploadGamePhoto,
  voteEntry,
  type Challenge,
  type ChallengeEntry,
} from "@/lib/api/games";
import { useMe } from "@/lib/auth/use-me";
import { mediaSrc } from "@/lib/media";

function EntryCard({
  entry,
  canVote,
  onVote,
  busy,
}: {
  entry: ChallengeEntry;
  canVote: boolean;
  onVote: () => void;
  busy: boolean;
}) {
  const t = useTranslations("games.challenge");
  return (
    <li className="border-trait bg-carte rounded-card flex flex-col gap-2 border p-2">
      {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
      <img
        src={mediaSrc(entry.photo, "medium", "thumb")}
        alt={t("photoOf", { name: entry.author.name })}
        loading="lazy"
        className="rounded-photo bg-poudre aspect-[3/4] w-full object-cover"
      />
      <span className="truncate px-1 font-bold">{entry.author.name}</span>
      <span className="text-small px-1">{t("votes", { count: entry.votes })}</span>
      {entry.mine ? (
        <span className="text-small text-hibiscus px-1 font-bold">{t("mine")}</span>
      ) : (
        <Button
          variant={entry.voted ? "secondary" : "primary"}
          disabled={!canVote || entry.voted || busy}
          onClick={onVote}
          fullWidth
        >
          <Heart aria-hidden size={20} weight={entry.voted ? "fill" : "bold"} />
          {entry.voted ? t("voted") : t("vote")}
        </Button>
      )}
    </li>
  );
}

export function FeaturedWinner({ featured }: { featured: Challenge["featured"] }) {
  const t = useTranslations("games.challenge");
  if (!featured) return null;
  return (
    <section
      aria-labelledby="winner-title"
      className="border-or bg-carte rounded-card flex items-center gap-4 border-2 p-4"
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
      <img
        src={mediaSrc(featured.winner.photo, "thumb", "medium")}
        alt=""
        className="petal size-24 shrink-0 object-cover"
      />
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-small inline-flex items-center gap-1 font-bold">
          <Trophy aria-hidden size={18} weight="fill" className="text-or" />
          {t("winnerLabel")}
        </span>
        <h2 id="winner-title" className="text-lead font-bold">
          {featured.winner.author.name}
        </h2>
        <span className="text-small text-prune-doux">
          {t("winnerOf", { theme: featured.theme, count: featured.winner.votes })}
        </span>
      </div>
    </section>
  );
}

/** The photo challenge of the week: the theme, take part, vote; last week's winner. */
export function ChallengeScreen() {
  const t = useTranslations("games.challenge");
  const locale = useLocale();
  const toast = useToast();
  const client = useQueryClient();
  const me = useMe();
  const query = useQuery({ queryKey: ["glow-challenge"], queryFn: getChallenge });
  const [busy, setBusy] = useState(false);
  const [caption, setCaption] = useState("");
  const [joined, setJoined] = useState(false);

  if (query.isPending) return <Skeleton className="rounded-card h-96" />;
  const found = query.data;
  const current = found?.current;
  const signedIn = Boolean(me.data);

  const run = async (action: () => Promise<Challenge>) => {
    setBusy(true);
    try {
      client.setQueryData(["glow-challenge"], await action());
      client.invalidateQueries({ queryKey: ["glow-me"] });
    } catch (failure) {
      toast(failure instanceof ApiError ? failure.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };
  const enter = (file: File | undefined) =>
    file &&
    run(async () => {
      const media = await uploadGamePhoto(file, "challenge_photo");
      const fresh = await enterChallenge({ photo_id: media.id, caption });
      setJoined(true);
      return fresh;
    });
  const end = (iso: string) =>
    new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(
      new Date(`${iso}T12:00:00`),
    );

  return (
    <div className="flex flex-col gap-6">
      <FeaturedWinner featured={found?.featured ?? null} />
      {!current ? (
        <EmptyState
          icon={<Camera size={48} weight="duotone" />}
          title={t("none")}
          description={t("noneHelp")}
        />
      ) : (
        <>
          <section className="bg-poudre rounded-card flex flex-col gap-3 p-5">
            <p className="text-small font-bold">{t("ofTheWeek")}</p>
            <div className="flex items-start gap-2">
              <h1 className="font-display text-headline flex-1 font-black">{current.theme}</h1>
              <SpeakButton text={`${current.theme}. ${current.description}`} />
            </div>
            {current.description && <p>{current.description}</p>}
            <p className="text-small text-prune-doux">
              {t("until", { date: end(current.ends_on) })}
            </p>
          </section>

          {joined && <Bloom label={t("joined")} className="self-center" />}
          {signedIn && !current.my_entry && (
            <section className="flex flex-col gap-3">
              <Input
                label={t("caption")}
                value={caption}
                maxLength={140}
                onChange={(event) => setCaption(event.target.value)}
              />
              <label
                className={`${busy ? "opacity-50" : ""} bg-hibiscus text-sur-hibiscus text-lead flex min-h-14 cursor-pointer items-center justify-center gap-3 rounded-full px-7 font-bold`}
              >
                <Camera aria-hidden size={24} weight="bold" />
                {busy ? t("sending") : t("join")}
                <input
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  disabled={busy}
                  onChange={(event) => enter(event.target.files?.[0])}
                />
              </label>
            </section>
          )}
          {current.my_entry && <p className="font-bold">{t("inTheGame")}</p>}
          {signedIn && (
            <p className="text-small" aria-live="polite">
              {t("votesLeft", { count: current.votes_left })}
            </p>
          )}

          {current.entries.length === 0 ? (
            <p className="text-prune-doux">{t("first")}</p>
          ) : (
            <ul className="grid grid-cols-2 gap-3">
              {current.entries.map((entry) => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  busy={busy}
                  canVote={signedIn && current.votes_left > 0}
                  onVote={() => run(() => voteEntry(entry.id))}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
