import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type"> & {
  selected?: boolean;
  icon?: ReactNode;
};

/** A pill that can be switched on and off (filters, choices). */
export function Chip({ selected = false, icon, className, children, ...props }: Props) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-4 font-bold transition-colors duration-150",
        selected
          ? "border-prune bg-prune text-lait"
          : "border-trait bg-poudre text-prune hover:border-prune-doux",
        className,
      )}
      {...props}
    >
      {icon && (
        <span aria-hidden className="inline-flex">
          {icon}
        </span>
      )}
      {children}
    </button>
  );
}
