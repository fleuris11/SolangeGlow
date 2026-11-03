import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

import { AutoplayVideo } from "./autoplay-video";

type Props = {
  src: string;
  /** Empty when the picture only decorates a text that says the same thing. */
  alt: string;
  /** A short muted loop played over the picture (never in data saver). */
  videoSrc?: string;
  /** Opens through the petal of the logo, once (solange-design, signature moment 1). */
  reveal?: boolean;
  /** The warm light of a photo on a night background: its dominant colour. */
  glow?: string;
  /** The picture is the top of the page: loaded first. */
  priority?: boolean;
  sizes?: string;
  className?: string;
  imageClassName?: string;
  children?: ReactNode;
};

/**
 * A photo (or short video) that fills its frame. The picture is there before any script: the
 * reveal is plain CSS, and starts already visible so it never delays the first paint.
 */
export function MediaHero({
  src,
  alt,
  videoSrc,
  reveal = false,
  glow,
  priority = false,
  sizes = "100vw",
  className,
  imageClassName,
  children,
}: Props) {
  return (
    <div
      className={cn("relative isolate", className)}
      style={glow ? ({ "--lueur": glow } as CSSProperties) : undefined}
    >
      {glow && <span aria-hidden className="sg-glow" />}
      <div
        className={cn(
          "relative size-full overflow-hidden",
          reveal && "sg-petal-reveal",
          imageClassName,
        )}
      >
        <Image
          src={src}
          alt={alt}
          fill
          priority={priority}
          sizes={sizes}
          className="object-cover"
        />
        {videoSrc && (
          <AutoplayVideo src={videoSrc} className="absolute inset-0 size-full object-cover" />
        )}
      </div>
      {children}
    </div>
  );
}
