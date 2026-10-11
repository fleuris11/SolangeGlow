"use client";

import { FloppyDisk } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { TradeIcon, TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { getTrades } from "@/lib/api/accounts";
import { ApiError } from "@/lib/api/client";
import { checkSlug, updateMyPro, type MyPro } from "@/lib/api/pros";
import { useSetMyPro } from "@/lib/pros/use-my-pro";

import { MediaField } from "./media-field";
import { fieldClass, SectionFrame } from "./section-frame";
import { VoiceRecorder } from "./voice-recorder";

const LANGUAGES = ["fr", "en", "fon", "yo", "guw", "gej", "ee", "bba", "ddn", "ha", "wo", "ln"];
const NETWORKS = ["instagram", "tiktok", "facebook", "whatsapp", "website"] as const;

/** Name, short link, trades, presentation (text and voice), photos, languages, networks. */
export function InfoSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.info");
  const tTrades = useTranslations("trades");
  const tLanguages = useTranslations("pros.languages");
  const toast = useToast();
  const setPro = useSetMyPro();
  const trades = useQuery({ queryKey: ["trades"], queryFn: getTrades, staleTime: 3_600_000 });

  const [name, setName] = useState(pro.business_name);
  const [slug, setSlug] = useState(pro.slug);
  const [slugHint, setSlugHint] = useState<string>();
  const [kind, setKind] = useState(pro.kind);
  const [chosen, setChosen] = useState(pro.trades.map((trade) => trade.key));
  const [bio, setBio] = useState(pro.bio);
  const [languages, setLanguages] = useState(pro.languages.map((language) => language.code));
  const [links, setLinks] = useState<Record<string, string>>({ ...pro.social_links });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

  const verifySlug = async () => {
    if (!slug || slug === pro.slug) return setSlugHint(undefined);
    try {
      const result = await checkSlug(slug);
      setSlugHint(result.available ? t("slugFree") : t("slugTaken", { suggestion: result.slug }));
    } catch {
      setSlugHint(undefined);
    }
  };

  const save = async () => {
    setSaving(true);
    setErrors({});
    try {
      setPro(
        await updateMyPro({
          business_name: name,
          slug,
          kind,
          trades: chosen,
          bio,
          languages: languages as never,
          social_links: links,
        }),
      );
      toast(t("saved"), "success");
    } catch (error) {
      if (error instanceof ApiError) {
        const field = error.code.startsWith("slug")
          ? "slug"
          : error.code.includes("social")
            ? "links"
            : "form";
        setErrors({ [field]: error.message });
      } else setErrors({ form: t("error") });
    } finally {
      setSaving(false);
    }
  };

  const tradeKeys = (trades.data ?? [])
    .map((trade) => trade.key)
    .filter((key): key is Trade => (TRADES as readonly string[]).includes(key));

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <MediaField
        field="photo"
        label={t("photo")}
        hint={t("photoHint")}
        media={pro.photo}
        accept="image/*"
      />
      <MediaField
        field="cover"
        label={t("cover")}
        hint={t("coverHint")}
        media={pro.cover}
        accept="image/*"
      />

      <Input
        label={t("name")}
        value={name}
        onChange={(event) => setName(event.target.value)}
        maxLength={80}
      />
      <Input
        label={t("slug")}
        hint={slugHint ?? t("slugHint", { link: `${pro.short_link.replace(/[^/]*$/, "")}${slug}` })}
        error={errors.slug}
        value={slug}
        onChange={(event) => setSlug(event.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
        onBlur={() => void verifySlug()}
        maxLength={40}
        autoCapitalize="none"
      />

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("kind")}</legend>
        <div className="flex flex-wrap gap-2">
          {(["independent", "business"] as const).map((value) => (
            <Chip key={value} selected={kind === value} onClick={() => setKind(value)}>
              {t(`kinds.${value}`)}
            </Chip>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("trades")}</legend>
        <div className="flex flex-wrap gap-2">
          {tradeKeys.map((key) => (
            <Chip
              key={key}
              selected={chosen.includes(key)}
              icon={<TradeIcon trade={key} size={24} />}
              onClick={() => setChosen(toggle(chosen, key))}
            >
              {tTrades(key)}
            </Chip>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-2">
        <label htmlFor="bio" className="font-bold">
          {t("bio")}
        </label>
        <textarea
          id="bio"
          rows={5}
          maxLength={1000}
          value={bio}
          onChange={(event) => setBio(event.target.value)}
          className={fieldClass}
          aria-describedby="bio-hint"
        />
        <p id="bio-hint" className="text-small text-prune-doux">
          {t("bioHint")}
        </p>
      </div>
      <MediaField
        field="bio_voice"
        label={t("bioVoice")}
        hint={t("bioVoiceHint")}
        media={pro.bio_voice}
        accept="audio/*"
      >
        {(upload) => <VoiceRecorder onRecorded={(file) => void upload(file, "voice.webm")} />}
      </MediaField>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-bold">{t("languages")}</legend>
        <div className="flex flex-wrap gap-2">
          {LANGUAGES.map((code) => (
            <Chip
              key={code}
              selected={languages.includes(code)}
              onClick={() => setLanguages(toggle(languages, code))}
            >
              {tLanguages(code as "fr")}
            </Chip>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 font-bold">{t("networks")}</legend>
        {NETWORKS.map((network) => (
          <Input
            key={network}
            label={t(`network.${network}`)}
            placeholder={t(`networkHint.${network}`)}
            value={links[network] ?? ""}
            onChange={(event) => setLinks({ ...links, [network]: event.target.value })}
            inputMode={network === "whatsapp" ? "tel" : network === "website" ? "url" : "text"}
            autoCapitalize="none"
          />
        ))}
        {errors.links && (
          <p role="alert" className="text-alerte font-bold">
            {errors.links}
          </p>
        )}
      </fieldset>

      {errors.form && (
        <p role="alert" className="text-alerte font-bold">
          {errors.form}
        </p>
      )}
      <Button size="lg" fullWidth disabled={saving} onClick={() => void save()}>
        <FloppyDisk aria-hidden size={24} weight="bold" />
        {t("save")}
      </Button>
    </SectionFrame>
  );
}
