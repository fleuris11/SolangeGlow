"use client";

import { CheckCircle, Camera, Crosshair, SignIn, Storefront, Van } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { LocationPicker } from "@/components/features/map/lazy";
import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Button, buttonClasses } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { SwitchRow } from "@/components/ui/switch-row";
import { getTrades } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { claimInvitation } from "@/lib/api/help";
import { becomePro, setMyLocation, setMyTravel, updateMyPro, uploadProMedia } from "@/lib/api/pros";
import { useMe } from "@/lib/auth/use-me";
import { Link, useRouter } from "@/lib/i18n/navigation";
import { useMapConfig } from "@/lib/pros/use-map-config";
import { useMyPro } from "@/lib/pros/use-my-pro";
import { rememberInvite, takeInvite } from "@/lib/prospects/invite";

const TOTAL = 4;
type Position = { latitude: number; longitude: number };

/** « Become a pro »: name, trades, place, photo. Then « Ma vitrine » to finish. */
export function BecomeProFlow({ invite }: { invite?: string }) {
  const t = useTranslations("pros.become");
  useEffect(() => {
    if (invite) rememberInvite(invite);
  }, [invite]);
  const tTrades = useTranslations("trades");
  const router = useRouter();
  const me = useMe();
  const existing = useMyPro();
  const trades = useQuery({ queryKey: ["trades"], queryFn: getTrades, staleTime: 3_600_000 });

  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"independent" | "business">("independent");
  const [chosen, setChosen] = useState<string[]>([]);
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [receives, setReceives] = useState(true);
  const [travels, setTravels] = useState(false);
  const [position, setPosition] = useState<Position | null>(null);
  const [source, setSource] = useState<"map" | "gps">("map");
  const [showMap, setShowMap] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [locating, setLocating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const photoInput = useRef<HTMLInputElement>(null);
  const config = useMapConfig(me.data?.country, showMap);

  if (me.isPending || existing.isPending) return <Skeleton className="rounded-card h-96" />;

  if (!me.data) {
    return (
      <div className="flex flex-col items-start gap-4">
        <h1 className="text-headline font-bold">{t("title")}</h1>
        <p>{t("signInFirst")}</p>
        <Link href="/auth?as=pro" className={buttonClasses({ size: "lg" })}>
          <SignIn aria-hidden size={24} weight="bold" />
          {t("signIn")}
        </Link>
      </div>
    );
  }

  const titles = [t("steps.name"), t("steps.trades"), t("steps.place"), t("steps.photo")];
  const helps = [t("help.name"), t("help.trades"), t("help.place"), t("help.photo")];
  const canContinue =
    (step === 1 && name.trim().length >= 2) ||
    (step === 2 && chosen.length > 0) ||
    (step === 3 && city.trim().length > 0 && (receives || travels)) ||
    step === 4;

  const locate = () => {
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

  const finish = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await becomePro({ business_name: name.trim(), kind, trades: chosen, city, district });
      if (position) await setMyLocation({ ...position, source });
      if (!receives) await updateMyPro({ receives_clients: false });
      if (travels) await setMyTravel({ travels_to_clients: true, radius_km: 10 });
      if (photo) await uploadProMedia("photo", photo);
      const code = takeInvite();
      if (code) await claimInvitation(code).catch(() => undefined);
      await existing.refetch();
      router.push("/pro");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : t("error"));
      setBusy(false);
    }
  };

  const tradeKeys = (trades.data ?? [])
    .map((trade) => trade.key)
    .filter((key): key is Trade => (TRADES as readonly string[]).includes(key));

  return (
    <div className="flex flex-col gap-6">
      <Stepper current={step} total={TOTAL} onBack={() => setStep(step - 1)} />
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline font-bold">{titles[step - 1]}</h1>
          <p className="text-prune-doux">{helps[step - 1]}</p>
        </div>
        <SpeakButton text={`${titles[step - 1]}. ${helps[step - 1]}`} />
      </div>

      {step === 1 && (
        <>
          <Input
            label={t("name")}
            placeholder={t("namePlaceholder")}
            value={name}
            maxLength={80}
            autoFocus
            onChange={(event) => setName(event.target.value)}
          />
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-bold">{t("kind")}</legend>
            <div className="flex flex-col gap-2">
              {(["independent", "business"] as const).map((value) => (
                <Chip key={value} selected={kind === value} onClick={() => setKind(value)}>
                  {t(`kinds.${value}`)}
                </Chip>
              ))}
            </div>
          </fieldset>
        </>
      )}

      {step === 2 && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {tradeKeys.map((key) => (
            <Chip
              key={key}
              selected={chosen.includes(key)}
              icon={<TradeIcon trade={key} size={28} />}
              onClick={() =>
                setChosen(chosen.includes(key) ? chosen.filter((k) => k !== key) : [...chosen, key])
              }
            >
              {tTrades(key)}
            </Chip>
          ))}
        </div>
      )}

      {step === 3 && (
        <>
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
            description={t("receivesText")}
            checked={receives}
            onChange={setReceives}
          />
          <SwitchRow
            icon={<Van size={28} weight="duotone" />}
            label={t("travels")}
            description={t("travelsText")}
            checked={travels}
            onChange={setTravels}
          />
          <div className="bg-poudre rounded-card flex flex-col gap-3 p-4">
            <p className="font-bold">{t("pointTitle")}</p>
            <p className="text-small">{receives ? t("pointHelp") : t("pointPrivate")}</p>
            <Button variant="secondary" disabled={locating} onClick={locate}>
              <Crosshair aria-hidden size={22} weight="bold" />
              {locating ? t("locating") : t("gps")}
            </Button>
            {!showMap ? (
              <Button variant="quiet" onClick={() => setShowMap(true)}>
                {t("placeOnMap")}
              </Button>
            ) : config.data ? (
              <LocationPicker
                key={source === "gps" && position ? `gps-${position.latitude}` : "map"}
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
          </div>
        </>
      )}

      {step === 4 && (
        <div className="flex flex-col items-start gap-3">
          <input
            ref={photoInput}
            type="file"
            accept="image/*"
            className="sr-only"
            tabIndex={-1}
            aria-label={t("photo")}
            onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
          />
          <Button variant="secondary" onClick={() => photoInput.current?.click()}>
            <Camera aria-hidden size={22} weight="bold" />
            {photo ? t("photoChosen", { name: photo.name }) : t("photo")}
          </Button>
          <p className="text-small text-prune-doux">{t("photoLater")}</p>
        </div>
      )}

      {error && (
        <p role="alert" className="text-alerte font-bold">
          {error}
        </p>
      )}
      <Button
        size="lg"
        fullWidth
        disabled={!canContinue || busy}
        onClick={() => (step < TOTAL ? setStep(step + 1) : void finish())}
      >
        {step < TOTAL ? t("next") : t("finish")}
      </Button>
    </div>
  );
}
