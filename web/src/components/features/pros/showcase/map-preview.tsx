"use client";

import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

// The map settings, MapLibre and the tiles are downloaded only after the tap.
const PlaceMap = dynamic(() => import("./place-map").then((m) => m.PlaceMap));

type Props = {
  name: string;
  latitude: number;
  longitude: number;
  country?: string | null;
  icon: ReactNode;
};

/** The map costs data: it is shown only when asked. */
export function MapPreview({ icon, ...props }: Props) {
  const t = useTranslations("pros.showcase");
  const [shown, setShown] = useState(false);
  if (shown) return <PlaceMap {...props} />;
  return (
    <Button variant="secondary" fullWidth onClick={() => setShown(true)}>
      {icon}
      {t("showMap")}
    </Button>
  );
}
