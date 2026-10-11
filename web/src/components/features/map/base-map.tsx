"use client";

/*
 * MapLibre map. Heavy (about 230 KB): never import this file directly, always through
 * next/dynamic, so it is downloaded only when a map is shown (ADR-004).
 */
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";

import type { MapConfig } from "@/lib/api/pros";
import { cn } from "@/lib/cn";

// MapLibre 6 draws tiles in a Web Worker: point it to the file published by the bundler.
maplibregl.setWorkerUrl(
  new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString(),
);

export type MapLibre = typeof maplibregl;

/** A colour of the design tokens (light or dark theme), for map layers and pins. */
export function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
}
export type MapInstance = maplibregl.Map;

/** The font of the map style (any style set in the admin), for our own labels. */
export function styleFont(map: MapInstance): string[] {
  for (const layer of map.getStyle().layers ?? []) {
    const font = layer.type === "symbol" ? layer.layout?.["text-font"] : undefined;
    if (Array.isArray(font) && font.every((name) => typeof name === "string")) {
      return font as string[];
    }
  }
  return ["Noto Sans Regular"];
}

type Props = {
  config: MapConfig;
  /** [longitude, latitude]; the default view of the country otherwise. */
  center?: [number, number];
  zoom?: number;
  /** Describes the map for screen readers. */
  label: string;
  onLoad?: (map: MapInstance, library: MapLibre) => void;
  className?: string;
};

export function BaseMap({ config, center, zoom, label, onLoad, className }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const loaded = useRef(onLoad);
  useEffect(() => {
    loaded.current = onLoad;
  });

  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: config.style_url,
      center: center ?? [config.longitude, config.latitude],
      zoom: zoom ?? config.zoom,
      attributionControl: { compact: true },
      // One finger scrolls the page on a phone; two fingers move the map.
      cooperativeGestures: true,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => loaded.current?.(map, maplibregl));
    return () => map.remove();
    // The map is created once; later moves are made through the map instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.style_url]);

  return (
    <div className="flex flex-col gap-1">
      <div
        ref={container}
        role="region"
        aria-label={label}
        className={cn("rounded-card bg-poudre h-72 w-full overflow-hidden", className)}
      />
      <p className="text-mention text-prune-doux">{config.attribution}</p>
    </div>
  );
}
