"use client";

import {
  CalendarDots,
  CaretRight,
  ChartBar,
  Crown,
  Gift,
  Megaphone,
  Package,
  Receipt,
  Stack,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { getAgenda } from "@/lib/api/booking";
import { ApiError } from "@/lib/api/client";
import { addPackage, getPackages, type GlowFeature } from "@/lib/api/glowpro";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney, parseMoney } from "@/lib/money";

import { PremiumGate, useGlowPro } from "./premium-gate";

const TOOLS: { href: string; key: string; icon: ReactNode; feature?: GlowFeature }[] = [
  { href: "/pro/agenda", key: "agenda", icon: <CalendarDots size={28} weight="duotone" /> },
  { href: "/pro/dashboard", key: "dashboard", icon: <ChartBar size={28} weight="duotone" /> },
  { href: "/pro/gift-cards", key: "giftCards", icon: <Gift size={28} weight="duotone" /> },
  { href: "/pro/invoices", key: "invoices", icon: <Receipt size={28} weight="duotone" /> },
  {
    href: "/pro/packages",
    key: "packages",
    icon: <Stack size={28} weight="duotone" />,
    feature: "client_file",
  },
  {
    href: "/pro/stock",
    key: "stock",
    icon: <Package size={28} weight="duotone" />,
    feature: "stock",
  },
  {
    href: "/pro/campaigns",
    key: "campaigns",
    icon: <Megaphone size={28} weight="duotone" />,
    feature: "campaigns",
  },
  { href: "/pro/plan", key: "plan", icon: <Crown size={28} weight="duotone" /> },
];

/** « My salon »: every Glow Pro tool in one place, Premium ones marked. */
export function SalonHub() {
  const t = useTranslations("glowpro.hub");
  const { has, data } = useGlowPro();
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex-1 font-bold">{t("title")}</h1>
        <SpeakButton text={t("title")} />
      </div>
      {data && <p className="text-prune-doux">{t("plan", { name: data.current.name })}</p>}
      <ul className="flex flex-col gap-2">
        {TOOLS.map((tool) => (
          <li key={tool.href}>
            <Link
              href={tool.href}
              className="border-trait bg-carte rounded-card flex min-h-16 items-center gap-4 border p-4"
            >
              <span aria-hidden className="text-hibiscus">
                {tool.icon}
              </span>
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{t(`tools.${tool.key as "agenda"}`)}</span>
                <span className="text-small text-prune-doux">
                  {t(`help.${tool.key as "agenda"}`)}
                </span>
              </span>
              {tool.feature && !has(tool.feature) && (
                <span className="bg-or text-sur-or text-small rounded-full px-2 py-1 font-bold">
                  {t("premium")}
                </span>
              )}
              <CaretRight aria-hidden size={20} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** « Packages »: sessions sold in advance (sold from the client file or the showcase). */
export function PackagesScreen() {
  const t = useTranslations("glowpro.packages");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Stack aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <PremiumGate feature="client_file" title={t("premiumTitle")} text={t("premiumText")}>
        <PackageList />
      </PremiumGate>
    </div>
  );
}

function PackageList() {
  const t = useTranslations("glowpro.packages");
  const locale = useLocale();
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["packages"], queryFn: getPackages });
  const services = useQuery({
    queryKey: ["agenda", "services"],
    queryFn: () => getAgenda({ start: new Date().toISOString().slice(0, 10), days: 1 }),
  });
  const [serviceId, setServiceId] = useState("");
  const [name, setName] = useState("");
  const [sessions, setSessions] = useState("5");
  const [price, setPrice] = useState("");
  const [installments, setInstallments] = useState("1");
  const [busy, setBusy] = useState(false);
  const service = services.data?.services.find((s) => s.id === serviceId);

  const save = async () => {
    const minor = parseMoney(price, service?.currency ?? "XOF");
    if (!service || !minor) return;
    setBusy(true);
    try {
      await addPackage({
        service_id: service.id,
        name: name || `${sessions} x ${service.name}`,
        sessions: Number(sessions),
        price_minor: minor,
        max_installments: Number(installments),
      });
      await queryClient.invalidateQueries({ queryKey: ["packages"] });
      toast(t("saved"), "success");
      setName("");
      setPrice("");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  const rows = query.data ?? [];
  return (
    <div className="flex flex-col gap-5">
      {rows.length === 0 ? (
        <EmptyState
          icon={<Stack size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((p) => (
            <li
              key={p.id}
              className="border-trait bg-carte rounded-card flex min-h-16 items-center gap-3 border p-3"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{p.name}</span>
                <span className="text-small text-prune-doux">
                  {t("line", {
                    sessions: p.sessions,
                    service: p.service_name,
                    times: p.max_installments,
                  })}
                </span>
              </span>
              <span className="font-bold">{formatMoney(p.price_minor, p.currency, locale)}</span>
            </li>
          ))}
        </ul>
      )}
      <section
        aria-labelledby="new-package"
        className="border-trait rounded-card flex flex-col gap-4 border p-4"
      >
        <h2 id="new-package" className="text-lead font-bold">
          {t("new")}
        </h2>
        <label className="flex flex-col gap-2 font-bold">
          {t("service")}
          <select
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            <option value="">{t("chooseService")}</option>
            {(services.data?.services ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <Input
          label={t("name")}
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label={t("sessions")}
            inputMode="numeric"
            value={sessions}
            onChange={(e) => setSessions(e.target.value.replace(/\D/g, ""))}
          />
          <Input
            label={t("price")}
            inputMode="decimal"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </div>
        <label className="flex flex-col gap-2 font-bold">
          {t("installments")}
          <select
            value={installments}
            onChange={(e) => setInstallments(e.target.value)}
            className="border-trait bg-carte min-h-12 rounded-[14px] border-2 px-3"
          >
            {[1, 2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {t("times", { count: n })}
              </option>
            ))}
          </select>
        </label>
        <Button
          size="lg"
          fullWidth
          disabled={busy || !serviceId || !price || Number(sessions) < 2}
          onClick={() => void save()}
        >
          {t("save")}
        </Button>
      </section>
    </div>
  );
}
