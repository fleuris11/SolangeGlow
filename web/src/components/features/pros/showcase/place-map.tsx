"use client";

import { useTranslations } from "next-intl";

import { PointMap } from "@/components/features/map/lazy";
import { Skeleton } from "@/components/ui/skeleton";
import { useMapConfig } from "@/lib/pros/use-map-config";

type Props = { name: string; latitude: number; longitude: number; country?: string | null };

/** The pro's place on the map (loaded after « See on the map »). */
export function PlaceMap({ name, latitude, longitude, country }: Props) {
  const t = useTranslations("pros.showcase");
  const config = useMapConfig(country);
  if (!config.data) return <Skeleton className="rounded-card h-72" />;
  return (
    <PointMap
      config={config.data}
      latitude={latitude}
      longitude={longitude}
      label={t("mapLabel", { name })}
    />
  );
}
