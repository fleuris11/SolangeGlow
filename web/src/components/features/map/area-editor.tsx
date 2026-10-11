"use client";

import type { GeoJSONSource, MapMouseEvent } from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { MapConfig } from "@/lib/api/pros";

import { BaseMap, token, type MapInstance } from "./base-map";

type Props = {
  config: MapConfig;
  center: [number, number] | undefined;
  /** Corners of the area, [longitude, latitude]. */
  points: number[][];
  onAdd: (point: number[]) => void;
  /** Radius around the salon, shown when no area is drawn. */
  radiusKm: number | null;
  label: string;
};

function circle([lng, lat]: [number, number], km: number): number[][] {
  const ring: number[][] = [];
  for (let step = 0; step <= 64; step++) {
    const angle = (step / 64) * 2 * Math.PI;
    const dLat = (km / 111.32) * Math.sin(angle);
    const dLng = (km / (111.32 * Math.cos((lat * Math.PI) / 180))) * Math.cos(angle);
    ring.push([lng + dLng, lat + dLat]);
  }
  return ring;
}

function shape(points: number[][], center: [number, number] | undefined, radiusKm: number | null) {
  let ring: number[][] | null = null;
  if (points.length >= 3) ring = [...points, points[0]!];
  else if (center && radiusKm) ring = circle(center, radiusKm);
  return {
    type: "FeatureCollection" as const,
    features: [
      ...(ring
        ? [
            {
              type: "Feature" as const,
              properties: {},
              geometry: { type: "Polygon" as const, coordinates: [ring] },
            },
          ]
        : []),
      ...points.map((point) => ({
        type: "Feature" as const,
        properties: {},
        geometry: { type: "Point" as const, coordinates: point },
      })),
    ],
  };
}

/** Travel area: a circle around the salon, or corners tapped one by one on the map. */
export function AreaEditor({ config, center, points, onAdd, radiusKm, label }: Props) {
  const mapRef = useRef<MapInstance | null>(null);

  useEffect(() => {
    const source = mapRef.current?.getSource("area") as GeoJSONSource | undefined;
    source?.setData(shape(points, center, radiusKm));
  }, [points, center, radiusKm]);

  return (
    <BaseMap
      config={config}
      center={center}
      zoom={center ? 11 : undefined}
      label={label}
      className="h-80"
      onLoad={(map, maplibre) => {
        mapRef.current = map;
        const color = token("hibiscus");
        map.addSource("area", { type: "geojson", data: shape(points, center, radiusKm) });
        map.addLayer({
          id: "area-fill",
          type: "fill",
          source: "area",
          filter: ["==", ["geometry-type"], "Polygon"],
          paint: { "fill-color": color, "fill-opacity": 0.15 },
        });
        map.addLayer({
          id: "area-line",
          type: "line",
          source: "area",
          filter: ["==", ["geometry-type"], "Polygon"],
          paint: { "line-color": color, "line-width": 3 },
        });
        map.addLayer({
          id: "area-corners",
          type: "circle",
          source: "area",
          filter: ["==", ["geometry-type"], "Point"],
          paint: {
            "circle-color": color,
            "circle-radius": 7,
            "circle-stroke-color": token("carte"),
            "circle-stroke-width": 2,
          },
        });
        if (center) new maplibre.Marker({ color: token("prune") }).setLngLat(center).addTo(map);
        map.on("click", (event: MapMouseEvent) => onAdd([event.lngLat.lng, event.lngLat.lat]));
      }}
    />
  );
}
