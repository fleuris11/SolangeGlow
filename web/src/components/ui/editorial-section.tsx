import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/cn";

type Ambiance = "jour" | "nuit" | "poudre" | "hibiscus" | "rouge";

const fields: Record<Ambiance, string> = {
  jour: "bg-lait text-prune",
  nuit: "bg-nuit text-prune sg-to-night",
  poudre: "bg-poudre text-prune",
  hibiscus: "bg-rouge text-sur-hibiscus",
  rouge: "bg-lait text-prune",
};

type Props = ComponentPropsWithoutRef<"section"> & { ambiance?: Ambiance };

/**
 * A full-width chapter of an editorial page. « nuit » keeps its night colours in both themes,
 * repaints every token inside it, and fades in from the day while scrolling where the browser
 * knows how (CSS scroll timeline, no script); elsewhere it is simply a night section.
 */
export function EditorialSection({ ambiance = "jour", className, children, ...props }: Props) {
  return (
    <section
      data-chapter
      data-ambiance={ambiance === "nuit" || ambiance === "rouge" ? ambiance : undefined}
      className={cn("relative w-full", fields[ambiance], className)}
      {...props}
    >
      {children}
    </section>
  );
}
