"use client";

import type { VideoTrack } from "livekit-client";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";

/** Shows one camera. The own camera is mirrored, like a mirror. */
export function TrackView({
  track,
  mirror = false,
  label,
  className,
}: {
  track: VideoTrack;
  mirror?: boolean;
  label: string;
  className?: string;
}) {
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const element = video.current;
    if (!element) return;
    track.attach(element);
    return () => {
      track.detach(element);
    };
  }, [track]);
  return (
    <video
      ref={video}
      aria-label={label}
      autoPlay
      playsInline
      muted
      className={cn("size-full object-cover", mirror && "-scale-x-100", className)}
    />
  );
}
