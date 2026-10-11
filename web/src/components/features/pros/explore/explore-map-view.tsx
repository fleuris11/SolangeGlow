"use client";

import { useTranslations } from "next-intl";

import { ExploreMap } from "@/components/features/map/lazy";
import { Skeleton } from "@/components/ui/skeleton";
import type { SearchQuery } from "@/lib/api/pros";
import { useRouter } from "@/lib/i18n/navigation";
import { useMapConfig } from "@/lib/pros/use-map-config";

type Props = { query: SearchQuery; country?: string; center?: [number, number] };

/** Map view of Explore: MapLibre is downloaded only here. */
export function ExploreMapView({ query, country, center }: Props) {
  const t = useTranslations("explore");
  const router = useRouter();
  const config = useMapConfig(country);
  if (!config.data) return <Skeleton className="rounded-card h-[60dvh]" />;
  return (
    <ExploreMap
      config={config.data}
      filters={query}
      center={center}
      label={t("mapLabel")}
      onOpen={(slug) => router.push(`/${slug}`)}
    />
  );
}
