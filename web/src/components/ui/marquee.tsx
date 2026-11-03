import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Props = {
  children: ReactNode;
  label: string;
  className?: string;
};

/**
 * A band that slides slowly (the trades of the home page). It stops under the finger, the
 * mouse or the keyboard; with reduced animations it becomes a list scrolled by hand. The copy
 * that makes the loop seamless is hidden from assistive technologies and from the keyboard.
 */
export function Marquee({ children, label, className }: Props) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn("sg-marquee [scrollbar-width:none] overflow-x-auto", className)}
    >
      <div className="sg-marquee-track flex w-max">
        <div className="flex shrink-0 items-center gap-8 pr-8">{children}</div>
        <div aria-hidden inert className="sg-marquee-copy flex shrink-0 items-center gap-8 pr-8">
          {children}
        </div>
      </div>
    </div>
  );
}
