import { cn } from "@/lib/cn";

/**
 * Placeholder shown while content loads. Purely decorative for assistive tech.
 * Whole screens use SkeletonShape, which takes the form of what is coming.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn("bg-poudre animate-shimmer rounded-card block", className)} />
  );
}
