"use client";

import {
  CheckCircle,
  ArrowCounterClockwise,
  Crosshair,
  FloppyDisk,
  Storefront,
  Van,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { AreaEditor, LocationPicker } from "@/components/features/map/lazy";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { setMyLocation, setMyTravel, updateMyPro, type MyPro } from "@/lib/api/pros";
import { currencyExponent } from "@/lib/money";
import { useMapConfig } from "@/lib/pros/use-map-config";
import { useSetMyPro } from "@/lib/pros/use-my-pro";

import { MediaField } from "./media-field";
import { fieldClass, SectionFrame } from "./section-frame";
import { VoiceRecorder } from "./voice-recorder";

const RADII = [3, 5, 10, 15, 20, 30];

/** Where clients find her: point on the map, address, landmarks, itinerary video, home visits. */
export function PlaceSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.place");
  const toast = useToast();
  const setPro = useSetMyPro();
  const config = useMapConfig(pro.place.country);
  const exponent = currencyExponent(pro.currency || "XOF");

  const [city, setCity] = useState(pro.place.city);
  const [district, setDistrict] = useState(pro.place.district);
  const [address, setAddress] = useState(pro.place.address ?? "");
  const [landmarks, setLandmarks] = useState(pro.place.landmarks);
  const [receives, setReceives] = useState(pro.place.receives_clients);
  const [position, setPosition] = useState(
    pro.place.latitude !== null && pro.place.longitude !== null
      ? { latitude: pro.place.latitude, longitude: pro.place.longitude }
      : null,
  );
  const [source, setSource] = useState<"map" | "gps">("map");
  const [travels, setTravels] = useState(pro.travel.travels_to_clients);
  const [mode, setMode] = useState<"radius" | "area">(pro.travel.area ? "area" : "radius");
  const [radius, setRadius] = useState(pro.travel.radius_km ?? 10);
  const [area, setArea] = useState<number[][]>(pro.travel.area?.slice(0, -1) ?? []);
  const [fee, setFee] = useState(
    pro.travel.fee_minor ? String(pro.travel.fee_minor / 10 ** exponent) : "",
  );
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const useGps = () => {
    if (!navigator.geolocation) return setError(t("gpsUnavailable"));
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (found) => {
        setLocating(false);
        setSource("gps");
        setPosition({ latitude: found.coords.latitude, longitude: found.coords.longitude });
      },
      () => {
        setLocating(false);
        setError(t("gpsUnavailable"));
      },
      { enableHighAccuracy: true, timeout: 20_000 },
    );
  };

  const save = async () => {
    setBusy(true);
    setError(undefined);
    try {
      let saved = await updateMyPro({
        city,
        district,
        address,
        landmarks,
        receives_clients: receives,
      });
      if (position) saved = await setMyLocation({ ...position, source });
      const feeMinor = fee.trim()
        ? Math.round(Number.parseFloat(fee.replace(",", ".")) * 10 ** exponent)
        : null;
      saved = await setMyTravel({
        travels_to_clients: travels,
        ...(travels && mode === "radius" ? { radius_km: radius } : {}),
        ...(travels && mode === "area" ? { area } : {}),
        fee_minor: Number.isFinite(feeMinor) ? feeMinor : null,
      });
      setPro(saved);
      toast(t("saved"), "success");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  const center: [number, number] | undefined = position
    ? [position.longitude, position.latitude]
    : undefined;

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
          label={t("city")}
          value={city}
          maxLength={80}
          onChange={(event) => setCity(event.target.value)}
        />
        <Input
          label={t("district")}
          value={district}
          maxLength={80}
          onChange={(event) => setDistrict(event.target.value)}
        />
      </div>

      <SwitchRow
        icon={<Storefront size={28} weight="duotone" />}
        label={t("receives")}
        description={receives ? t("receivesOn") : t("receivesOff")}
        checked={receives}
        onChange={setReceives}
      />

      <section aria-labelledby="point-title" className="flex flex-col gap-3">
        <h2 id="point-title" className="text-title font-bold">
          {t("point")}
        </h2>
        <p className="text-prune-doux">{receives ? t("pointHelp") : t("pointPrivate")}</p>
        <Button variant="secondary" disabled={locating} onClick={useGps}>
          <Crosshair aria-hidden size={22} weight="bold" />
          {locating ? t("locating") : t("gps")}
        </Button>
        {config.data ? (
          <LocationPicker
            // Moved again only when the GPS gives a new point (a tap keeps the map as it is).
            key={
              source === "gps" && position
                ? `gps-${position.latitude},${position.longitude}`
                : "map"
            }
            config={config.data}
            value={position}
            onChange={(value) => {
              setSource("map");
              setPosition(value);
            }}
            label={t("mapLabel")}
          />
        ) : (
          <Skeleton className="rounded-card h-80" />
        )}
        {position && (
          <p className="text-small flex items-center gap-2 font-bold" role="status">
            <CheckCircle aria-hidden size={20} weight="fill" className="text-feuille" />
            {t("pointSet")}
          </p>
        )}
      </section>

      {receives && (
        <>
          <Input
            label={t("address")}
            hint={t("addressHint")}
            value={address}
            maxLength={200}
            onChange={(event) => setAddress(event.target.value)}
          />
          <div className="flex flex-col gap-2">
            <label htmlFor="landmarks" className="font-bold">
              {t("landmarks")}
            </label>
            <textarea
              id="landmarks"
              rows={3}
              maxLength={500}
              placeholder={t("landmarksPlaceholder")}
              value={landmarks}
              onChange={(event) => setLandmarks(event.target.value)}
              className={fieldClass}
            />
          </div>
          <MediaField
            field="landmarks_voice"
            label={t("landmarksVoice")}
            hint={t("landmarksVoiceHint")}
            media={pro.place.landmarks_voice}
            accept="audio/*"
          >
            {(upload) => <VoiceRecorder onRecorded={(file) => void upload(file, "voice.webm")} />}
          </MediaField>
          <MediaField
            field="itinerary_video"
            label={t("video")}
            hint={t("videoHint")}
            media={pro.place.itinerary_video}
            accept="video/*"
            capture="environment"
          />
        </>
      )}

      <section aria-labelledby="travel-title" className="flex flex-col gap-3">
        <h2 id="travel-title" className="text-title font-bold">
          {t("travelTitle")}
        </h2>
        <SwitchRow
          icon={<Van size={28} weight="duotone" />}
          label={t("travels")}
          description={t("travelsText")}
          checked={travels}
          onChange={setTravels}
        />
        {travels && (
          <>
            <div className="flex flex-wrap gap-2">
              <Chip selected={mode === "radius"} onClick={() => setMode("radius")}>
                {t("modeRadius")}
              </Chip>
              <Chip selected={mode === "area"} onClick={() => setMode("area")}>
                {t("modeArea")}
              </Chip>
            </div>
            {mode === "radius" ? (
              <div className="flex flex-wrap gap-2">
                {RADII.map((km) => (
                  <Chip key={km} selected={radius === km} onClick={() => setRadius(km)}>
                    {t("km", { km })}
                  </Chip>
                ))}
              </div>
            ) : (
              <>
                <p className="text-prune-doux">{t("areaHelp")}</p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="quiet"
                    disabled={!area.length}
                    onClick={() => setArea(area.slice(0, -1))}
                  >
                    <ArrowCounterClockwise aria-hidden size={20} />
                    {t("undo")}
                  </Button>
                  <Button variant="quiet" disabled={!area.length} onClick={() => setArea([])}>
                    {t("clear")}
                  </Button>
                </div>
              </>
            )}
            {config.data && (
              <AreaEditor
                config={config.data}
                center={center}
                points={mode === "area" ? area : []}
                onAdd={(point) => mode === "area" && setArea((current) => [...current, point])}
                radiusKm={mode === "radius" ? radius : null}
                label={t("areaLabel")}
              />
            )}
            <Input
              label={t("fee", { currency: pro.currency === "EUR" ? "€" : "FCFA" })}
              hint={t("feeHint")}
              inputMode="decimal"
              value={fee}
              onChange={(event) => setFee(event.target.value)}
            />
          </>
        )}
      </section>

      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
        <FloppyDisk aria-hidden size={24} weight="bold" />
        {t("save")}
      </Button>
    </SectionFrame>
  );
}
