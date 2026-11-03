"use client";

import { useEffect, useState } from "react";

import { prefersReducedMotion } from "@/lib/motion";

type Props = { src: string; poster?: string; className?: string };

/**
 * A short silent loop. Nothing is downloaded before the page is ready, nor at all in data
 * saver or with reduced animations: the picture underneath stays on screen.
 */
export function AutoplayVideo({ src, poster, className }: Props) {
  const [play, setPlay] = useState(false);

  useEffect(() => {
    const saver = document.documentElement.dataset.dataSaver === "true";
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read once from the browser
    setPlay(!saver && !prefersReducedMotion());
  }, []);

  if (!play) return null;
  return (
    <video
      src={src}
      poster={poster}
      muted
      loop
      autoPlay
      playsInline
      preload="metadata"
      aria-hidden
      className={className}
    />
  );
}
