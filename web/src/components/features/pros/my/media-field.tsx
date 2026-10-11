"use client";

import { CircleNotch, Trash, UploadSimple, WarningCircle } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useId, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { removeProMedia, uploadProMedia, type MediaField as Field } from "@/lib/api/pros";
import { mediaSrc, videoSrc, voiceSrc, type Media } from "@/lib/media";
import { useSetMyPro } from "@/lib/pros/use-my-pro";

type Props = {
  field: Field;
  label: string;
  hint?: string;
  media: Media | null;
  accept: string;
  /** Opens the camera on phones ("environment" = back camera). */
  capture?: "user" | "environment";
  /** Extra way to give the file (e.g. the voice recorder). */
  children?: (upload: (file: Blob, name?: string) => Promise<void>) => ReactNode;
};

/** One picture, video or voice note of the showcase: shown, replaced, removed. */
export function MediaField({ field, label, hint, media, accept, capture, children }: Props) {
  const t = useTranslations("pros.my.media");
  const toast = useToast();
  const setPro = useSetMyPro();
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const upload = async (file: Blob, name?: string) => {
    setBusy(true);
    setError(undefined);
    try {
      setPro(await uploadProMedia(field, file, name));
      toast(t("sent"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      setPro(await removeProMedia(field));
    } finally {
      setBusy(false);
    }
  };

  const status = media?.status;
  const waiting = status === "pending" || status === "processing";
  const image = mediaSrc(media, "medium", "thumb");
  const video = media?.kind === "video" ? videoSrc(media, true) : undefined;
  const voice = media?.kind === "audio" ? voiceSrc(media) : undefined;

  return (
    <div className="border-trait rounded-card flex flex-col gap-3 border p-4">
      <div>
        <p id={id} className="font-bold">
          {label}
        </p>
        {hint && <p className="text-small text-prune-doux">{hint}</p>}
      </div>

      {waiting && (
        <p className="text-small flex items-center gap-2" role="status">
          <CircleNotch aria-hidden size={20} className="animate-spin" />
          {t("processing")}
        </p>
      )}
      {status === "rejected" && (
        <p className="text-alerte text-small flex items-center gap-2" role="alert">
          <WarningCircle aria-hidden size={20} weight="fill" />
          {t(
            `rejected.${media?.error === "too_short" || media?.error === "too_long" ? media.error : "other"}`,
          )}
        </p>
      )}
      {image && !video && (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img src={image} alt="" className="max-h-56 w-full rounded-2xl object-cover" />
      )}
      {video && (
        <video
          src={video}
          controls
          preload="none"
          className="w-full rounded-2xl"
          aria-labelledby={id}
        />
      )}
      {voice && (
        <audio src={voice} controls preload="none" className="w-full" aria-labelledby={id}>
          <track kind="captions" />
        </audio>
      )}
      {error && (
        <p role="alert" className="text-alerte text-small font-bold">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          ref={input}
          type="file"
          accept={accept}
          capture={capture}
          className="sr-only"
          aria-labelledby={id}
          tabIndex={-1}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void upload(file);
          }}
        />
        <Button variant="secondary" disabled={busy} onClick={() => input.current?.click()}>
          <UploadSimple aria-hidden size={22} weight="bold" />
          {media ? t("replace") : t("choose")}
        </Button>
        {children?.(upload)}
        {media && (
          <Button variant="quiet" disabled={busy} onClick={() => void remove()}>
            <Trash aria-hidden size={22} />
            {t("remove")}
          </Button>
        )}
      </div>
    </div>
  );
}
