"use client";

import type { FeatureCollection, Point } from "geojson";
import type { GeoJSONSource, MapLayerMouseEvent } from "maplibre-gl";
import { useEffect, useRef } from "react";

import { getMapPoints, type MapConfig, type MapQuery } from "@/lib/api/pros";

import { BaseMap, styleFont, token, type MapInstance } from "./base-map";

type Props = {
  config: MapConfig;
  /** Filters of the list (words, trade, open now…); the box comes from the map. */
  filters: Omit<MapQuery, "bbox">;
  center?: [number, number];
  label: string;
  onOpen: (slug: string) => void;
  onTruncated?: (truncated: boolean) => void;
};

/** Pros of the visible area, grouped in circles when they are close (MapLibre clusters). */
export function ExploreMap({ config, filters, center, label, onOpen, onTruncated }: Props) {
  const filtersRef = useRef(filters);
  const mapRef = useRef<MapInstance | null>(null);

  const load = async (map: MapInstance) => {
    const bounds = map.getBounds();
    const bbox = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()]
      .map((value) => value.toFixed(5))
      .join(",");
    try {
      const data = await getMapPoints({ ...filtersRef.current, bbox });
      (map.getSource("pros") as GeoJSONSource | undefined)?.setData(
        data as unknown as FeatureCollection,
      );
      onTruncated?.(data.truncated);
    } catch {
      // The list stays available; the map will try again at the next move.
    }
  };

  // New filters (words, trade…): the points of the visible area are asked again.
  const key = JSON.stringify(filters);
  useEffect(() => {
    filtersRef.current = filters;
    if (mapRef.current) void load(mapRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <BaseMap
      config={config}
      center={center}
      zoom={center ? 13 : undefined}
      label={label}
      className="h-[60dvh]"
      onLoad={(map) => {
        mapRef.current = map;
        const pin = token("hibiscus");
        const group = token("prune");
        const halo = token("carte");
        const font = styleFont(map);
        map.addSource("pros", {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
          cluster: true,
          clusterRadius: 44,
          clusterMaxZoom: 15,
        });
        map.addLayer({
          id: "clusters",
          type: "circle",
          source: "pros",
          filter: ["has", "point_count"],
          paint: {
            "circle-color": group,
            "circle-radius": ["step", ["get", "point_count"], 18, 10, 24, 50, 30],
            "circle-stroke-color": halo,
            "circle-stroke-width": 3,
          },
        });
        map.addLayer({
          id: "cluster-count",
          type: "symbol",
          source: "pros",
          filter: ["has", "point_count"],
          layout: {
            "text-field": ["get", "point_count_abbreviated"],
            "text-size": 15,
            "text-font": font,
          },
          paint: { "text-color": halo },
        });
        map.addLayer({
          id: "pros",
          type: "circle",
          source: "pros",
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": pin,
            "circle-radius": 11,
            "circle-stroke-color": halo,
            "circle-stroke-width": 3,
          },
        });
        map.addLayer({
          id: "pros-name",
          type: "symbol",
          source: "pros",
          filter: ["!", ["has", "point_count"]],
          layout: {
            "text-field": ["get", "name"],
            "text-font": font,
            "text-size": 13,
            "text-offset": [0, 1.4],
            "text-anchor": "top",
          },
          paint: { "text-color": group, "text-halo-color": halo, "text-halo-width": 2 },
        });
        map.on("click", "clusters", async (event: MapLayerMouseEvent) => {
          const feature = event.features?.[0];
          const source = map.getSource("pros") as GeoJSONSource;
          if (!feature) return;
          const zoom = await source.getClusterExpansionZoom(feature.properties.cluster_id);
          map.easeTo({
            center: (feature.geometry as Point).coordinates as [number, number],
            zoom,
          });
        });
        map.on("click", "pros", (event: MapLayerMouseEvent) => {
          const slug = event.features?.[0]?.properties.slug;
          if (slug) onOpen(String(slug));
        });
        for (const layer of ["clusters", "pros"]) {
          map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
        }
        map.on("moveend", () => void load(map));
        void load(map);
      }}
    />
  );
}
