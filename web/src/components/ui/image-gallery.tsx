"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { useRef, useState, type UIEvent } from "react";

import { cn } from "@/lib/cn";

export type GalleryImage = { src: string; alt: string };

type Props = {
  images: GalleryImage[];
  sizes?: string;
  /** The first picture is the top of the page: loaded first. */
  priority?: boolean;
  className?: string;
};

/**
 * Photos side by side: the browser's own scroll carries the swipe (and its momentum), so it
 * stays smooth on a small phone. Double tap zooms, and the phone's pinch still works.
 */
export function ImageGallery({
  images,
  sizes = "(min-width: 1024px) 50vw, 100vw",
  priority = false,
  className,
}: Props) {
  const t = useTranslations("ui.gallery");
  const track = useRef<HTMLDivElement>(null);
  const [current, setCurrent] = useState(0);
  const [zoomed, setZoomed] = useState(false);

  function onScroll(event: UIEvent<HTMLDivElement>) {
    const { scrollLeft, clientWidth } = event.currentTarget;
    if (clientWidth) setCurrent(Math.round(scrollLeft / clientWidth));
  }

  function go(index: number) {
    const element = track.current;
    element?.scrollTo?.({ left: index * element.clientWidth });
  }

  return (
    <div className={cn("relative", className)}>
      <div
        ref={track}
        role="group"
        aria-label={t("label")}
        tabIndex={0}
        onScroll={onScroll}
        className="flex snap-x snap-mandatory [scrollbar-width:none] overflow-x-auto"
      >
        {images.map((image, index) => (
          <div
            key={image.src}
            className="relative aspect-[4/5] w-full shrink-0 snap-center overflow-hidden"
          >
            <Image
              src={image.src}
              alt={image.alt}
              fill
              sizes={sizes}
              priority={priority && index === 0}
              onDoubleClick={() => setZoomed((value) => !value)}
              className={cn(
                "duration-opening ease-sortie object-cover transition-transform",
                zoomed && index === current && "scale-[1.8]",
              )}
            />
          </div>
        ))}
      </div>
      {images.length > 1 && (
        <ol
          aria-label={t("position", { current: current + 1, total: images.length })}
          className="absolute inset-x-0 bottom-1 flex justify-center"
        >
          {images.map((image, index) => (
            <li key={image.src}>
              <button
                type="button"
                onClick={() => go(index)}
                aria-label={t("show", { number: index + 1 })}
                aria-current={index === current}
                className="flex size-6 items-center justify-center"
              >
                <span
                  aria-hidden
                  className={cn(
                    "bg-carte block size-2 rounded-full",
                    index !== current && "opacity-50",
                  )}
                />
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
