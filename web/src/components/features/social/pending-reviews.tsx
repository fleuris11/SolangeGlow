"use client";

import { Star, StarHalf } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { VoiceRecorder } from "@/components/features/pros/my/voice-recorder";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  createReview,
  getMedia,
  getPendingReviews,
  uploadMedia,
  type PendingReview,
} from "@/lib/api/social";

function ReviewForm({ item, onDone }: { item: PendingReview; onDone: () => void }) {
  const t = useTranslations("social.reviews");
  const toast = useToast();
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const [voiceId, setVoiceId] = useState<string>();
  const [photoId, setPhotoId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const upload = async (file: Blob, purpose: "review_photo" | "review_voice") => {
    const named = file instanceof File ? file : new File([file], "voice.webm", { type: file.type });
    const sent = await uploadMedia(named, purpose);
    const media = await getMedia(sent.id);
    if (purpose === "review_voice") setVoiceId(media.id);
    else setPhotoId(media.id);
  };

  const send = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await createReview({
        kind: item.kind,
        transaction_id: item.transaction_id,
        rating,
        text,
        photo_id: photoId ?? null,
        voice_id: voiceId ?? null,
      });
      toast(t("thanks"), "success");
      onDone();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-bold">{t("stars")}</legend>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={rating === value}
              aria-label={t("starsValue", { count: value })}
              onClick={() => setRating(value)}
              className="inline-flex size-12 items-center justify-center rounded-full"
            >
              <Star
                aria-hidden
                size={32}
                weight={value <= rating ? "fill" : "regular"}
                className={value <= rating ? "text-or" : "text-prune-doux"}
              />
            </button>
          ))}
        </div>
      </fieldset>
      <label htmlFor={`review-${item.transaction_id}`} className="font-bold">
        {t("text")}
      </label>
      <textarea
        id={`review-${item.transaction_id}`}
        rows={3}
        maxLength={2000}
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none"
      />
      <div className="flex flex-wrap gap-2">
        <label className="border-prune text-prune inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full border-2 px-5 font-bold">
          <StarHalf aria-hidden size={20} />
          {photoId ? t("photoAdded") : t("addPhoto")}
          <input
            type="file"
            accept="image/*"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file, "review_photo");
            }}
          />
        </label>
        <VoiceRecorder onRecorded={(blob) => void upload(blob, "review_voice")} />
      </div>
      {voiceId && <p className="text-small text-prune-doux">{t("voiceAdded")}</p>}
      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button size="lg" fullWidth disabled={!rating || busy} onClick={() => void send()}>
        {t("send")}
      </Button>
    </div>
  );
}

/** Finished bookings and orders she can still review (verified reviews only). */
export function PendingReviews() {
  const t = useTranslations("social.reviews");
  const locale = useLocale();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["pending-reviews"], queryFn: getPendingReviews });
  if (query.isPending) return <Skeleton className="rounded-card h-48" />;
  const items = query.data ?? [];
  if (!items.length) {
    return (
      <EmptyState
        icon={<Star size={48} weight="duotone" />}
        title={t("emptyTitle")}
        description={t("emptyText")}
      />
    );
  }
  return (
    <ul className="flex flex-col gap-4">
      {items.map((item) => (
        <li
          key={item.transaction_id}
          className="border-trait rounded-card flex flex-col gap-3 border p-4"
        >
          <p className="font-bold">{item.pro_name}</p>
          <p className="text-small text-prune-doux">
            {item.label},{" "}
            {new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(
              new Date(item.finished_at),
            )}
          </p>
          <ReviewForm
            item={item}
            onDone={() => void queryClient.invalidateQueries({ queryKey: ["pending-reviews"] })}
          />
        </li>
      ))}
    </ul>
  );
}
