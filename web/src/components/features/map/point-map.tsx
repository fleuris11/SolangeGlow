"use client";

import type { MapConfig } from "@/lib/api/pros";
import { BaseMap, token } from "./base-map";

type Props = { config: MapConfig; latitude: number; longitude: number; label: string };

/** The pro's place, one pin. */
export function PointMap({ config, latitude, longitude, label }: Props) {
  return (
    <BaseMap
      config={config}
      center={[longitude, latitude]}
      zoom={16}
      label={label}
      onLoad={(map, maplibre) => {
        new maplibre.Marker({ color: token("hibiscus") })
          .setLngLat([longitude, latitude])
          .addTo(map);
      }}
    />
  );
}
