"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
};

/** Bottom sheet: focus is trapped inside, Escape and the close button dismiss it. */
export function Sheet({ open, onOpenChange, title, description, children }: Props) {
  const t = useTranslations("common");
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="bg-voile fixed inset-0 z-50 animate-[fade-in_180ms_ease-out]" />
        <Dialog.Content className="bg-carte text-prune rounded-t-sheet shadow-float pb-safe fixed inset-x-0 bottom-0 z-50 mx-auto max-h-[85dvh] w-full max-w-[640px] animate-[sheet-up_200ms_var(--ease-out-soft)] overflow-y-auto">
          <div aria-hidden className="bg-trait mx-auto mt-3 h-1.5 w-12 rounded-full" />
          <div className="flex items-start justify-between gap-4 px-6 pt-4">
            <div>
              <Dialog.Title className="text-title font-bold">{title}</Dialog.Title>
              <Dialog.Description className={description ? "text-prune-doux mt-1" : "sr-only"}>
                {description ?? title}
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label={t("close")}
              className="hover:bg-poudre -mr-2 inline-flex size-12 shrink-0 items-center justify-center rounded-full"
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
