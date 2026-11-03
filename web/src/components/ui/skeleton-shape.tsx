import { cn } from "@/lib/cn";

import { Skeleton } from "./skeleton";

type Shape = "post" | "pro" | "product" | "hero" | "list";

/** Placeholders with the shape of what is coming, so nothing jumps when it arrives. */
export function SkeletonShape({ shape, className }: { shape: Shape; className?: string }) {
  return (
    <div aria-hidden className={cn("flex w-full flex-col gap-3", className)}>
      {shape === "post" && (
        <>
          <div className="flex items-center gap-2">
            <Skeleton className="sg-petal-shape size-10" />
            <Skeleton className="h-4 w-36" />
          </div>
          <Skeleton className="rounded-photo aspect-[4/5] w-full" />
          <Skeleton className="h-4 w-2/3" />
        </>
      )}
      {shape === "pro" && (
        <div className="flex gap-3">
          <Skeleton className="rounded-photo aspect-[4/5] w-28 shrink-0" />
          <div className="flex flex-1 flex-col gap-2 pt-1">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      )}
      {shape === "product" && (
        <>
          <Skeleton className="rounded-photo aspect-square w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-5 w-1/3" />
        </>
      )}
      {shape === "hero" && (
        <Skeleton className="aspect-[4/5] w-full rounded-none lg:aspect-[16/9]" />
      )}
      {shape === "list" &&
        ["a", "b", "c"].map((row) => (
          <div key={row} className="flex items-center gap-3">
            <Skeleton className="sg-petal-shape size-12 shrink-0" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          </div>
        ))}
    </div>
  );
}
