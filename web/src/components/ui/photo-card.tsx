import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = {
  src: string;
  alt: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  /** The dominant colour of the photo: a soft warm light behind the card on night sections. */
  glow?: string;
  /** Height over width, 4:5 by default (publications). */
  ratio?: "4/5" | "1/1" | "16/9";
  sizes?: string;
  priority?: boolean;
  className?: string;
  /** Interactive content over the photo (a link stretched over the whole card, for example). */
  children?: ReactNode;
};

/** A card led by its photo: the text only sits on the calm veil at the bottom. */
export function PhotoCard({
  src,
  alt,
  title,
  subtitle,
  glow,
  ratio = "4/5",
  sizes = "(min-width: 1024px) 33vw, 90vw",
  priority = false,
  className,
  children,
}: Props) {
  return (
    <figure
      className={cn("relative isolate m-0", className)}
      style={glow ? ({ "--lueur": glow } as CSSProperties) : undefined}
    >
      {glow && <span aria-hidden className="sg-glow" />}
      <div
        className="rounded-photo relative overflow-hidden"
        style={{ aspectRatio: ratio.replace("/", " / ") }}
      >
        <Image
          src={src}
          alt={alt}
          fill
          sizes={sizes}
          priority={priority}
          className="object-cover"
        />
        {(title || subtitle) && (
          <figcaption
            data-ambiance="nuit"
            className="bg-voile-photo absolute inset-x-0 bottom-0 p-4"
          >
            {title && <span className="text-title block font-bold">{title}</span>}
            {subtitle && <span className="text-small block">{subtitle}</span>}
          </figcaption>
        )}
        {children}
      </div>
    </figure>
  );
}
