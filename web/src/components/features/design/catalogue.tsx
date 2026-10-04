"use client";

import {
  ArrowCounterClockwise,
  CalendarCheck,
  ChatsCircle,
  Heart,
  MapPin,
  Package,
} from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Portrait } from "@/components/features/illustrations/portrait";
import { TradeIcon, TRADES } from "@/components/features/trades/trade-icon";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Bloom } from "@/components/ui/bloom";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { CodeInput } from "@/components/ui/code-input";
import { EmptyState } from "@/components/ui/empty-state";
import { IconLabel } from "@/components/ui/icon-label";
import { Input } from "@/components/ui/input";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { Stepper } from "@/components/ui/stepper";
import { useToast } from "@/components/ui/toast";

/** Every ui/ component with realistic examples. Rendered once per theme on /design. */
export function Catalogue({ theme }: { theme: "light" | "dark" }) {
  const t = useTranslations("design");
  const tTrades = useTranslations("trades");
  const toast = useToast();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [step, setStep] = useState(2);
  const [chips, setChips] = useState<string[]>(["braids"]);
  const [bloomKey, setBloomKey] = useState(0);
  const [codeError, setCodeError] = useState<string>();
  const id = (name: string) => `${theme}-${name}`;

  return (
    <div className="flex flex-col gap-10">
      <Section id={id("colors")} title={t("sections.colors")}>
        <ul className="grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-2">
          {[
            "hibiscus",
            "prune",
            "prune-doux",
            "lait",
            "poudre",
            "carte",
            "or",
            "feuille",
            "alerte",
            "trait",
          ].map((token) => (
            <li key={token} className="flex items-center gap-2">
              <span
                aria-hidden
                className="border-trait size-10 shrink-0 rounded-full border"
                style={{ background: `var(--${token})` }}
              />
              <code className="text-mention whitespace-nowrap">--{token}</code>
            </li>
          ))}
        </ul>
      </Section>

      <Section id={id("type")} title={t("sections.type")}>
        <p className="font-display text-hero font-black">Solange</p>
        <p className="font-display text-display font-black">{t("sample.display")}</p>
        <p className="text-headline font-bold">{t("sample.headline")}</p>
        <p className="text-title font-bold">{t("sample.title")}</p>
        <p className="text-lead">{t("sample.lead")}</p>
        <p>{t("sample.body")}</p>
        <p className="text-small text-prune-doux">{t("sample.small")}</p>
        <p className="text-mention text-prune-doux">{t("sample.mention")}</p>
      </Section>

      <Section id={id("button")} title="Button">
        <div className="flex flex-wrap gap-3">
          <Button icon={<CalendarCheck size={22} weight="bold" />}>{t("sample.book")}</Button>
          <Button variant="secondary">{t("sample.secondary")}</Button>
          <Button variant="quiet">{t("sample.quiet")}</Button>
          <Button disabled>{t("sample.disabled")}</Button>
        </div>
        <Button size="lg" fullWidth>
          {t("sample.pay")}
        </Button>
      </Section>

      <Section id={id("icon-label")} title="IconLabel">
        <div className="flex flex-wrap gap-6">
          <IconLabel icon={<MapPin size={22} weight="duotone" className="text-hibiscus" />}>
            Fidjrossè, Cotonou
          </IconLabel>
          <IconLabel layout="stacked" icon={<ChatsCircle size={28} weight="duotone" />}>
            {t("sample.messages")}
          </IconLabel>
          {TRADES.slice(0, 3).map((trade) => (
            <IconLabel
              key={trade}
              layout="stacked"
              icon={<TradeIcon trade={trade} size={32} className="text-hibiscus" />}
            >
              {tTrades(trade)}
            </IconLabel>
          ))}
        </div>
      </Section>

      <Section id={id("speak")} title="SpeakButton">
        <div className="flex items-center gap-3">
          <p className="flex-1">{t("sample.receiptCode")}</p>
          <SpeakButton text={t("sample.receiptCode")} always />
        </div>
      </Section>

      <Section id={id("price")} title="PriceTag">
        <div className="flex flex-wrap items-baseline gap-6">
          <PriceTag amountMinor={15000} currency="XOF" size="lg" />
          <PriceTag amountMinor={2500} currency="EUR" size="lg" />
          <PriceTag amountMinor={8000} currency="XOF" prefix={t("sample.from")} />
        </div>
      </Section>

      <Section id={id("avatar")} title="Avatar">
        <div className="flex flex-wrap items-end gap-4">
          <Avatar
            name="Aïcha"
            size="xl"
            halo
            picture={<Portrait skin={4} look="braids" outfit="or" />}
          />
          <Avatar
            name="Gloria"
            size="lg"
            picture={<Portrait skin={3} look="makeup" outfit="hibiscus" />}
          />
          <Avatar name="Sènami Hounkpè" size="md" />
          <Avatar name="Clarisse" size="sm" halo picture={<Portrait skin={2} look="afro" />} />
        </div>
      </Section>

      <Section id={id("chip")} title="Chip">
        <div className="flex flex-wrap gap-2">
          {TRADES.map((trade) => (
            <Chip
              key={trade}
              selected={chips.includes(trade)}
              icon={<TradeIcon trade={trade} size={22} />}
              onClick={() =>
                setChips((current) =>
                  current.includes(trade)
                    ? current.filter((c) => c !== trade)
                    : [...current, trade],
                )
              }
            >
              {tTrades(trade)}
            </Chip>
          ))}
        </div>
      </Section>

      <Section id={id("input")} title="Input">
        <Input label={t("sample.nameLabel")} placeholder="Aïcha" hint={t("sample.nameHint")} />
        <Input
          label={t("sample.phoneLabel")}
          type="tel"
          defaultValue="+229 01 97"
          error={t("sample.phoneError")}
        />
      </Section>

      <Section id={id("code")} title="CodeInput">
        <CodeInput
          label={t("sample.codeLabel")}
          error={codeError}
          onComplete={(code) => setCodeError(code === "123456" ? undefined : t("sample.codeError"))}
        />
      </Section>

      <Section id={id("sheet")} title="Sheet">
        <Button variant="secondary" onClick={() => setSheetOpen(true)}>
          {t("sample.openSheet")}
        </Button>
        <Sheet
          open={sheetOpen}
          onOpenChange={setSheetOpen}
          title={t("sample.sheetTitle")}
          description={t("sample.sheetText")}
        >
          <Button fullWidth onClick={() => setSheetOpen(false)}>
            {t("sample.sheetCta")}
          </Button>
        </Sheet>
      </Section>

      <Section id={id("stepper")} title="Stepper">
        <Stepper current={step} total={3} onBack={() => setStep((s) => Math.max(1, s - 1))} />
        <Button variant="quiet" onClick={() => setStep((s) => (s % 3) + 1)}>
          {t("sample.nextStep")}
        </Button>
      </Section>

      <Section id={id("toast")} title="Toast">
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => toast(t("sample.toastSaved"))}>
            {t("sample.showToast")}
          </Button>
          <Button variant="quiet" onClick={() => toast(t("sample.toastWarning"), "warning")}>
            {t("sample.showWarning")}
          </Button>
        </div>
      </Section>

      <Section id={id("badge")} title="Badge">
        <div className="flex flex-wrap gap-2">
          <Badge tone="glow">Glow</Badge>
          <Badge tone="star">Star</Badge>
          <Badge tone="icon">{t("sample.levelIcon")}</Badge>
          <Badge tone="verified">{t("sample.verified")}</Badge>
        </div>
      </Section>

      <Section id={id("skeleton")} title="Skeleton">
        <div className="flex items-center gap-3">
          <Skeleton className="petal size-16 rounded-none" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-2/3 rounded-full" />
            <Skeleton className="h-4 w-1/3 rounded-full" />
          </div>
        </div>
      </Section>

      <Section id={id("empty")} title="EmptyState">
        <EmptyState
          icon={<Package size={48} weight="duotone" />}
          title={t("sample.emptyTitle")}
          description={t("sample.emptyText")}
          action={<Button>{t("sample.emptyCta")}</Button>}
          className="border-trait rounded-card border"
        />
      </Section>

      <Section id={id("bloom")} title={t("sections.bloom")}>
        <div className="flex items-center gap-6">
          <Bloom key={bloomKey} label={t("sample.bloom")} />
          <Button
            variant="quiet"
            icon={<ArrowCounterClockwise size={22} weight="bold" />}
            onClick={() => setBloomKey((k) => k + 1)}
          >
            {t("sample.replay")}
          </Button>
        </div>
      </Section>

      <Section id={id("locale")} title="LocaleSwitcher">
        <LocaleSwitcher />
      </Section>

      <Section id={id("bottom-nav")} title="BottomNav">
        <p className="text-prune-doux flex items-center gap-2">
          <Heart aria-hidden size={20} weight="duotone" className="text-hibiscus" />
          {t("sample.bottomNav")}
        </p>
      </Section>
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <h3 id={id} className="text-lead border-trait border-b pb-2 font-bold">
        {title}
      </h3>
      {children}
    </section>
  );
}
