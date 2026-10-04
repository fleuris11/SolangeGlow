import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = {
  icon: ReactNode;
  children: ReactNode;
  /** Stacked = icon above the word (navigation); inline = side by side. */
  layout?: "inline" | "stacked";
  className?: string;
};

/** An icon always paired with a word, so the meaning never depends on reading alone. */
export function IconLabel({ icon, children, layout = "inline", className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center",
        layout === "stacked" ? "flex-col gap-1 text-center" : "gap-2",
        className,
      )}
    >
      <span aria-hidden className="inline-flex shrink-0">
        {icon}
      </span>
      <span>{children}</span>
    </span>
  );
}
