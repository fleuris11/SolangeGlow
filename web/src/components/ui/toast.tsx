"use client";

import { CheckCircle, Info, WarningCircle, X } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

type Tone = "success" | "info" | "warning";
type ToastItem = { id: number; tone: Tone; message: string };

const ToastContext = createContext<((message: string, tone?: Tone) => void) | null>(null);

const icons = {
  success: <CheckCircle aria-hidden size={24} weight="fill" className="text-feuille shrink-0" />,
  info: <Info aria-hidden size={24} weight="fill" className="text-prune-doux shrink-0" />,
  warning: <WarningCircle aria-hidden size={24} weight="fill" className="text-alerte shrink-0" />,
};

/** Short confirmations ("Saved", "Published"), announced politely to screen readers. */
export function ToastProvider({
  children,
  duration = 5000,
}: {
  children: ReactNode;
  duration?: number;
}) {
  const t = useTranslations("common");
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const show = useCallback((message: string, tone: Tone = "success") => {
    nextId.current += 1;
    const id = nextId.current;
    setItems((current) => [...current.slice(-2), { id, tone, message }]);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-28 z-[60] flex flex-col items-center gap-2 px-4 lg:bottom-8"
      >
        {items.map((item) => (
          <ToastCard
            key={item.id}
            item={item}
            duration={duration}
            onDismiss={dismiss}
            closeLabel={t("close")}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({
  item,
  duration,
  onDismiss,
  closeLabel,
}: {
  item: ToastItem;
  duration: number;
  onDismiss: (id: number) => void;
  closeLabel: string;
}) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(item.id), duration);
    return () => window.clearTimeout(timer);
  }, [item.id, duration, onDismiss]);

  return (
    <div className="bg-carte border-trait shadow-float rounded-card pointer-events-auto flex w-full max-w-[480px] animate-[fade-in_180ms_ease-out] items-center gap-3 border-2 py-2 pr-2 pl-4">
      {icons[item.tone]}
      <p className="flex-1 font-bold">{item.message}</p>
      <button
        type="button"
        onClick={() => onDismiss(item.id)}
        aria-label={closeLabel}
        className="hover:bg-poudre inline-flex size-12 shrink-0 items-center justify-center rounded-full"
      >
        <X aria-hidden size={20} />
      </button>
    </div>
  );
}

export function useToast() {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside <ToastProvider>");
  return show;
}
