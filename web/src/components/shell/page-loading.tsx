import { useTranslations } from "next-intl";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Shown the very moment a link is touched, while the server prepares the next page: the
 * screen answers at once instead of staying still (loading.tsx of each group of pages).
 */
export function PageLoading() {
  const t = useTranslations("common");
  return (
    <div role="status" className="flex w-full flex-col gap-4 py-2">
      <span className="sr-only">{t("loading")}</span>
      <Skeleton className="h-9 w-2/3 max-w-80" />
      <Skeleton className="h-5 w-1/2 max-w-64" />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Skeleton className="aspect-[4/5]" />
        <Skeleton className="aspect-[4/5] max-md:hidden" />
        <Skeleton className="aspect-[4/5] max-md:hidden" />
      </div>
    </div>
  );
}
