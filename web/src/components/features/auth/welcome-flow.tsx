"use client";

import { ArrowRight, Check, MapPin } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import { Portrait } from "@/components/features/illustrations/portrait";
import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Bloom } from "@/components/ui/bloom";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { completeOnboarding, getTrades } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { useMe, useSetMe } from "@/lib/auth/use-me";
import { cn } from "@/lib/cn";
import { CITIES } from "@/lib/demo/data";
import { useRouter } from "@/lib/i18n/navigation";
import { routing, type Locale } from "@/lib/i18n/routing";
import { usePreferences } from "@/lib/preferences/preferences-provider";

import { ErrorMessage } from "./error-message";

type Mode = "client" | "pro";

/** At most three screens: who I am (and my trades), my language, my city. */
export function WelcomeFlow({ as }: { as?: Mode }) {
  const t = useTranslations("welcome");
  const tTrades = useTranslations("trades");
  const tLocales = useTranslations("locales");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const { data: me, isPending } = useMe();
  const setMe = useSetMe();
  const prefs = usePreferences();
  const trades = useQuery({ queryKey: ["trades", locale], queryFn: getTrades });

  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<Mode | null>(as ?? null);
  const [chosenTrades, setChosenTrades] = useState<string[]>([]);
  const [language, setLanguage] = useState<Locale>(locale);
  const [city, setCity] = useState(prefs.city);
  const [otherCity, setOtherCity] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  // Only for signed-in people who have not finished the welcome yet.
  useEffect(() => {
    if (isPending || done) return;
    if (!me) router.replace("/auth");
    else if (!me.onboarding_required) router.replace("/");
  }, [me, isPending, done, router]);

  const tradeOptions =
    trades.data?.map((trade) => ({ key: trade.key, name: trade.name })) ??
    TRADES.map((key) => ({ key, name: tTrades(key) }));

  const canContinue =
    step === 1 ? mode === "client" || (mode === "pro" && chosenTrades.length > 0) : true;

  const finish = async () => {
    setError(undefined);
    setBusy(true);
    const finalCity = otherCity.trim() || city;
    try {
      const updated = await completeOnboarding({
        mode: mode ?? "client",
        trades: mode === "pro" ? chosenTrades : undefined,
        language,
        city: finalCity,
      });
      prefs.update({ city: finalCity });
      setDone(true);
      setMe(updated);
    } catch (err) {
      setError(err instanceof ApiError && err.body.message ? err.body.message : t("error"));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <section
        aria-labelledby="done-title"
        className="flex flex-col items-center gap-6 py-8 text-center"
      >
        <Bloom label={t("done.title")} size={160} />
        <h1 id="done-title" className="font-display text-display font-black">
          {t("done.title")}
        </h1>
        <p className="text-lead text-prune-doux max-w-[32ch]">
          {mode === "pro" ? t("done.pro") : t("done.client")}
        </p>
        <Button
          size="lg"
          fullWidth
          icon={<ArrowRight size={22} weight="bold" />}
          onClick={() => router.replace("/", { locale: language })}
        >
          {t("done.cta")}
        </Button>
      </section>
    );
  }

  const titles = [t("role.title"), t("language.title"), t("city.title")];
  const title = titles[step - 1] ?? "";

  return (
    <section aria-labelledby="welcome-title" className="flex flex-col gap-6">
      <Stepper current={step} total={3} onBack={() => setStep((s) => Math.max(1, s - 1))} />
      <div className="flex items-start justify-between gap-3">
        <h1 id="welcome-title" className="font-display text-headline font-black">
          {title}
        </h1>
        <SpeakButton text={title} always />
      </div>

      {step === 1 && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <BigChoice
              selected={mode === "client"}
              onClick={() => setMode("client")}
              picture={<Portrait skin={4} look="makeup" outfit="hibiscus" />}
              label={t("role.client")}
            />
            <BigChoice
              selected={mode === "pro"}
              onClick={() => setMode("pro")}
              picture={
                <span className="text-hibiscus flex size-full items-center justify-center">
                  <TradeIcon trade="braids" size={64} />
                </span>
              }
              label={t("role.pro")}
            />
          </div>
          {mode === "pro" && (
            <fieldset className="flex min-w-0 flex-col gap-3">
              <legend className="mb-3 font-bold">{t("role.trades")}</legend>
              <div className="flex flex-wrap gap-2">
                {tradeOptions.map((trade) => (
                  <Chip
                    key={trade.key}
                    selected={chosenTrades.includes(trade.key)}
                    icon={<TradeIcon trade={trade.key as Trade} size={22} />}
                    onClick={() =>
                      setChosenTrades((current) =>
                        current.includes(trade.key)
                          ? current.filter((key) => key !== trade.key)
                          : [...current, trade.key],
                      )
                    }
                  >
                    {trade.name}
                  </Chip>
                ))}
              </div>
            </fieldset>
          )}
        </>
      )}

      {step === 2 && (
        <div role="radiogroup" aria-label={t("language.title")} className="flex flex-col gap-3">
          {routing.locales.map((code) => (
            <button
              key={code}
              type="button"
              role="radio"
              aria-checked={language === code}
              lang={code}
              onClick={() => setLanguage(code)}
              className={cn(
                "rounded-card text-lead flex min-h-16 items-center justify-between gap-3 border-2 px-5 font-bold",
                language === code ? "border-prune bg-prune text-lait" : "border-trait bg-carte",
              )}
            >
              {tLocales(code)}
              {language === code && <Check aria-hidden size={24} weight="bold" />}
            </button>
          ))}
        </div>
      )}

      {step === 3 && (
        <>
          <div role="group" aria-label={t("city.title")} className="flex flex-wrap gap-2">
            {CITIES.map((name) => (
              <Chip
                key={name}
                selected={!otherCity && city === name}
                icon={<MapPin size={20} weight="duotone" />}
                onClick={() => {
                  setCity(name);
                  setOtherCity("");
                }}
              >
                {name}
              </Chip>
            ))}
          </div>
          <Input
            label={t("city.other")}
            value={otherCity}
            onChange={(event) => setOtherCity(event.target.value)}
            maxLength={80}
            autoComplete="address-level2"
          />
        </>
      )}

      <ErrorMessage message={error} />

      <Button
        size="lg"
        fullWidth
        disabled={!canContinue || busy}
        onClick={() => (step < 3 ? setStep(step + 1) : void finish())}
      >
        {step < 3 ? t("next") : t("finish")}
      </Button>
    </section>
  );
}

function BigChoice({
  selected,
  onClick,
  picture,
  label,
}: {
  selected: boolean;
  onClick: () => void;
  picture: ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        "rounded-card flex flex-col items-center gap-3 border-2 p-4 text-center font-bold",
        selected ? "border-hibiscus bg-poudre" : "border-trait bg-carte",
      )}
    >
      <span className="petal bg-poudre block size-24 overflow-hidden">{picture}</span>
      <span className="text-lead">{label}</span>
      <span
        aria-hidden
        className={cn(
          "inline-flex size-7 items-center justify-center rounded-full border-2",
          selected ? "border-hibiscus bg-hibiscus text-sur-hibiscus" : "border-trait",
        )}
      >
        {selected && <Check size={16} weight="bold" />}
      </span>
    </button>
  );
}
