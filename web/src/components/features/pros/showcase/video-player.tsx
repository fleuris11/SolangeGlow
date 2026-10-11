"use client";

import { Play } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { mediaSrc, videoSrc, type Media } from "@/lib/media";
import { usePreferences } from "@/lib/preferences/preferences-provider";

/**
 * A video that never starts by itself: its picture first, played on tap. In data saver
 * mode the low quality is played (Module 11).
 */
export function VideoPlayer({ media, label }: { media: Media; label: string }) {
  const t = useTranslations("pros.showcase");
  const { dataSaver } = usePreferences();
  const [playing, setPlaying] = useState(false);
  const poster = mediaSrc(media, dataSaver ? "thumb" : "medium", "large");
  const source = videoSrc(media, dataSaver);
  if (!source) return null;

  if (playing) {
    return (
      <video
        src={source}
        poster={poster}
        controls
        autoPlay
        playsInline
        aria-label={label}
        className="rounded-card bg-prune aspect-video w-full"
      />
    );
  }
  return (
    <button
      type="button"
      onClick={() => setPlaying(true)}
      className="rounded-card bg-prune relative flex aspect-video w-full items-center justify-center overflow-hidden"
    >
      {poster && (
        // eslint-disable-next-line @next/next/no-img-element -- already resized by the backend
        <img
          src={poster}
          alt=""
          loading="lazy"
          className="absolute inset-0 size-full object-cover"
        />
      )}
      <span className="bg-hibiscus text-sur-hibiscus relative inline-flex min-h-12 items-center gap-2 rounded-full px-5 font-bold">
        <Play aria-hidden size={22} weight="fill" />
        {t("playVideo", { label })}
      </span>
    </button>
  );
}
