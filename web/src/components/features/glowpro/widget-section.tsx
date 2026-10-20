"use client";

import { Code, Copy } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { SwitchRow } from "@/components/ui/switch-row";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getWidget, saveWidget } from "@/lib/api/glowpro";

import { PremiumGate } from "./premium-gate";

/** The booking on her own website, in her colour, only on the websites she lists. */
export function WidgetSection() {
  const t = useTranslations("glowpro.widget");
  return (
    <section
      aria-labelledby="widget"
      className="border-trait bg-carte rounded-card flex flex-col gap-4 border p-4"
    >
      <h2 id="widget" className="text-title flex items-center gap-2 font-bold">
        <Code aria-hidden size={28} weight="duotone" className="text-hibiscus" />
        {t("title")}
      </h2>
      <PremiumGate feature="widget" title={t("premiumTitle")} text={t("premiumText")}>
        <WidgetForm />
      </PremiumGate>
    </section>
  );
}

function WidgetForm() {
  const t = useTranslations("glowpro.widget");
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["widget"], queryFn: getWidget });
  const [color, setColor] = useState<string | null>(null);
  const [domains, setDomains] = useState<string | null>(null);
  const [active, setActive] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const data = query.data;
  if (!data) return null;

  const save = async () => {
    setBusy(true);
    try {
      await saveWidget({
        color: color ?? data.color,
        allowed_domains: (domains ?? data.allowed_domains.join("\n"))
          .split(/[\s,]+/)
          .map((d) => d.trim())
          .filter(Boolean),
        is_active: active ?? data.is_active,
      });
      await queryClient.invalidateQueries({ queryKey: ["widget"] });
      toast(t("saved"), "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-prune-doux">{t("help")}</p>
      <label className="flex items-center gap-3 font-bold">
        <input
          type="color"
          value={color ?? data.color}
          onChange={(e) => setColor(e.target.value.toUpperCase())}
          className="border-trait size-12 rounded-full border-2"
        />
        {t("color")}
      </label>
      <label className="flex flex-col gap-2 font-bold">
        {t("domains")}
        <textarea
          rows={3}
          value={domains ?? data.allowed_domains.join("\n")}
          onChange={(e) => setDomains(e.target.value)}
          placeholder={t("domainsPlaceholder")}
          className="border-trait bg-carte rounded-[14px] border-2 p-3 font-normal"
        />
        <span className="text-small text-prune-doux font-normal">{t("domainsHelp")}</span>
      </label>
      <SwitchRow
        icon={<Code size={26} weight="duotone" />}
        label={t("active")}
        description={t("activeHelp")}
        checked={active ?? data.is_active}
        onChange={setActive}
      />
      <Button size="lg" fullWidth disabled={busy} onClick={() => void save()}>
        {t("save")}
      </Button>
      <div className="flex flex-col gap-2">
        <p className="font-bold">{t("code")}</p>
        <pre className="bg-poudre text-small overflow-x-auto rounded-2xl p-3" tabIndex={0}>
          {data.snippet}
        </pre>
        <Button
          variant="secondary"
          fullWidth
          onClick={() =>
            void navigator.clipboard
              ?.writeText(data.snippet)
              .then(() => toast(t("copied"), "success"))
          }
        >
          <Copy aria-hidden size={22} />
          {t("copy")}
        </Button>
      </div>
    </div>
  );
}
