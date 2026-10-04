import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = {
  icon: ReactNode;
  title: string;
  /** Invitation to act: what to do next. */
  description?: string;
  action?: ReactNode;
  className?: string;
};

/** An empty screen is an invitation to act, centred on purpose. */
export function EmptyState({ icon, title, description, action, className }: Props) {
  return (
    <section className={cn("flex flex-col items-center gap-4 px-4 py-12 text-center", className)}>
      <span
        aria-hidden
        className="bg-poudre text-hibiscus petal inline-flex size-24 items-center justify-center"
      >
        {icon}
      </span>
      <h2 className="text-title font-bold">{title}</h2>
      {description && <p className="text-prune-doux max-w-[34ch]">{description}</p>}
      {action}
    </section>
  );
}
