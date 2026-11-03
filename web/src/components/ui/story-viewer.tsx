"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { CaretLeft, CaretRight, X } from "@phosphor-icons/react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useRef, useState, type PointerEvent, type ReactNode } from "react";

import { FLICK_VELOCITY } from "@/lib/motion";
import { cn } from "@/lib/cn";

export type Story = {
  id: string;
  src: string;
  alt: string;
  caption?: string;
  /** Who posted it, what to do next: shown over the story. */
  header?: ReactNode;
  action?: ReactNode;
};

type Props = {
  stories: Story[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  startAt?: number;
};

const SWIPE_DISTANCE = 60;

/**
 * Stories on the full screen. Nothing advances by itself: someone who reads slowly decides
 * when to go on, with a swipe or the two large buttons. A flick down closes.
 */
export function StoryViewer({ stories, open, onOpenChange, title, startAt = 0 }: Props) {
  const t = useTranslations("ui.stories");
  const [index, setIndex] = useState(startAt);
  const drag = useRef<{ x: number; y: number; at: number; id: number } | null>(null);
  const story = stories[index];

  function move(step: number) {
    const next = index + step;
    if (next < 0) return;
    if (next >= stories.length) onOpenChange(false);
    else setIndex(next);
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    // A second finger is ignored: it would make the story jump.
    if (drag.current) return;
    drag.current = { x: event.clientX, y: event.clientY, at: event.timeStamp, id: event.pointerId };
  }

  function onPointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = drag.current;
    if (!start || start.id !== event.pointerId) return;
    drag.current = null;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    const velocity = Math.abs(dy) / Math.max(event.timeStamp - start.at, 1);
    if (dy > SWIPE_DISTANCE || (dy > 0 && velocity > FLICK_VELOCITY * 5)) onOpenChange(false);
    else if (Math.abs(dx) > SWIPE_DISTANCE) move(dx < 0 ? 1 : -1);
  }

  if (!story) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Content
          data-ambiance="nuit"
          aria-describedby={undefined}
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerCancel={() => (drag.current = null)}
          className="bg-nuit sg-sheet-in fixed inset-0 z-50 touch-pan-y overflow-hidden"
        >
          <Dialog.Title className="sr-only">{title}</Dialog.Title>
          <Image
            key={story.id}
            src={story.src}
            alt={story.alt}
            fill
            sizes="100vw"
            priority
            className="object-contain"
          />
          <div className="absolute inset-x-0 top-0 flex flex-col gap-3 p-3">
            <div
              role="progressbar"
              aria-label={t("position", { current: index + 1, total: stories.length })}
              aria-valuenow={index + 1}
              aria-valuemin={1}
              aria-valuemax={stories.length}
              className="flex gap-1"
            >
              {stories.map((item, position) => (
                <span
                  key={item.id}
                  className={cn(
                    "bg-prune h-1 flex-1 rounded-full",
                    position > index && "opacity-40",
                  )}
                />
              ))}
            </div>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0 flex-1">{story.header}</div>
              <Dialog.Close
                aria-label={t("close")}
                className="bg-voile-photo inline-flex size-12 shrink-0 items-center justify-center rounded-full"
              >
                <X aria-hidden size={24} />
              </Dialog.Close>
            </div>
          </div>
          <div className="bg-voile-photo pb-safe absolute inset-x-0 bottom-0 flex flex-col gap-3 p-4">
            {story.caption && <p className="text-lead font-bold">{story.caption}</p>}
            {story.action}
            <div className="flex justify-between gap-3">
              <button
                type="button"
                onClick={() => move(-1)}
                disabled={index === 0}
                className="press inline-flex min-h-12 items-center gap-2 font-bold disabled:opacity-40"
              >
                <CaretLeft aria-hidden size={24} />
                {t("previous")}
              </button>
              <button
                type="button"
                onClick={() => move(1)}
                className="press inline-flex min-h-12 items-center gap-2 font-bold"
              >
                {index === stories.length - 1 ? t("finish") : t("next")}
                <CaretRight aria-hidden size={24} />
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
