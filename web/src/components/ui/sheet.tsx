"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useRef, type PointerEvent, type ReactNode } from "react";

import { FLICK_VELOCITY } from "@/lib/motion";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
};

const DISMISS_DISTANCE = 120;
// Pulled upward past its place, the sheet follows less and less instead of hitting a wall.
const UPWARD_FRICTION = 0.2;

/**
 * Bottom sheet: focus is trapped inside, Escape and the close button dismiss it, and so does
 * pulling the handle down, by distance or by a simple flick.
 */
export function Sheet({ open, onOpenChange, title, description, children }: Props) {
  const t = useTranslations("common");
  const content = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; at: number; id: number; moved: number } | null>(null);

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (drag.current) return;
    drag.current = { y: event.clientY, at: event.timeStamp, id: event.pointerId, moved: 0 };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    if (content.current) content.current.style.transition = "none";
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const start = drag.current;
    if (!start || start.id !== event.pointerId || !content.current) return;
    const moved = event.clientY - start.y;
    start.moved = moved;
    const shown = moved < 0 ? moved * UPWARD_FRICTION : moved;
    // On the element itself: a CSS variable would recalculate everything inside the sheet.
    content.current.style.transform = `translateY(${shown}px)`;
  }

  function onPointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = drag.current;
    if (!start || start.id !== event.pointerId || !content.current) return;
    drag.current = null;
    const velocity = start.moved / Math.max(event.timeStamp - start.at, 1);
    content.current.style.transition = "";
    content.current.style.transform = "";
    if (start.moved >= DISMISS_DISTANCE || velocity > FLICK_VELOCITY) onOpenChange(false);
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="bg-voile sg-fade-in fixed inset-0 z-50" />
        <Dialog.Content
          ref={content}
          className="bg-carte text-prune rounded-t-sheet shadow-float pb-safe sg-sheet-in sg-sheet fixed inset-x-0 bottom-0 z-50 mx-auto max-h-[85dvh] w-full max-w-[640px] overflow-y-auto"
        >
          <div
            aria-hidden
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            className="flex h-8 cursor-grab touch-none justify-center pt-3"
          >
            <span className="bg-trait h-1.5 w-12 rounded-full" />
          </div>
          <div className="flex items-start justify-between gap-4 px-6 pt-1">
            <div>
              <Dialog.Title className="text-title font-bold">{title}</Dialog.Title>
              <Dialog.Description className={description ? "text-prune-doux mt-1" : "sr-only"}>
                {description ?? title}
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label={t("close")}
              className="hover:bg-poudre press -mr-2 inline-flex size-12 shrink-0 items-center justify-center rounded-full"
            >
              <X aria-hidden size={24} />
            </Dialog.Close>
          </div>
          <div className="px-6 pt-4 pb-8">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export { Sheet as BottomSheet };
