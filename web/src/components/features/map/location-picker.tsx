"use client";

import type { MapMouseEvent, Marker } from "maplibre-gl";
import { useRef } from "react";

import type { MapConfig } from "@/lib/api/pros";

import { BaseMap, token } from "./base-map";

type Position = { latitude: number; longitude: number };

type Props = {
  config: MapConfig;
  value: Position | null;
  onChange: (position: Position) => void;
  label: string;
};

/** Tap the map (or drag the pin) to place the salon's door. */
export function LocationPicker({ config, value, onChange, label }: Props) {
  const marker = useRef<Marker | null>(null);

  return (
    <BaseMap
      config={config}
      center={value ? [value.longitude, value.latitude] : undefined}
      zoom={value ? 17 : undefined}
      label={label}
      className="h-80"
      onLoad={(map, maplibre) => {
        const place = (longitude: number, latitude: number) => {
          if (!marker.current) {
            const pin = new maplibre.Marker({ color: token("hibiscus"), draggable: true })
              .setLngLat([longitude, latitude])
              .addTo(map);
            pin.on("dragend", () => {
              const point = pin.getLngLat();
              onChange({ latitude: point.lat, longitude: point.lng });
            });
            marker.current = pin;
          } else {
            marker.current.setLngLat([longitude, latitude]);
          }
        };
        if (value) place(value.longitude, value.latitude);
        map.on("click", (event: MapMouseEvent) => {
          place(event.lngLat.lng, event.lngLat.lat);
          onChange({ latitude: event.lngLat.lat, longitude: event.lngLat.lng });
        });
      }}
    />
  );
}
