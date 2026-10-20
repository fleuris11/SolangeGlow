"use client";

import {
  EnvelopeSimple,
  Megaphone,
  PaperPlaneTilt,
  Plus,
  WhatsappLogo,
} from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { SpeakButton } from "@/components/ui/speak-button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import {
  addCampaign,
  getAudience,
  getCampaigns,
  sendCampaign,
  type Campaign,
} from "@/lib/api/glowpro";
import { cn } from "@/lib/cn";

import { PremiumGate } from "./premium-gate";

type Segment = Campaign["segment"];
const SEGMENTS: Segment[] = ["inactive", "birthday", "package_low", "all"];

/** « Campaigns »: a message to the clients who said yes, by e-mail or WhatsApp. */
export function CampaignsScreen() {
  const t = useTranslations("glowpro.campaigns");
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <h1 className="text-headline flex flex-1 items-center gap-2 font-bold">
          <Megaphone aria-hidden size={30} weight="duotone" className="text-hibiscus" />
          {t("title")}
        </h1>
        <SpeakButton text={t("title")} />
      </div>
      <PremiumGate feature="campaigns" title={t("premiumTitle")} text={t("premiumText")}>
        <CampaignList />
      </PremiumGate>
    </div>
  );
}

function CampaignList() {
  const t = useTranslations("glowpro.campaigns");
  const tSegment = useTranslations("glowpro.segments");
  const locale = useLocale();
  const query = useQuery({ queryKey: ["campaigns"], queryFn: getCampaigns });
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<Campaign | null>(null);
  const rows = query.data ?? [];
  return (
    <div className="flex flex-col gap-4">
      <p className="text-prune-doux">{t("help")}</p>
      <Button size="lg" fullWidth onClick={() => setCreating(true)}>
        <Plus aria-hidden size={24} weight="bold" />
        {t("new")}
      </Button>
      {query.isPending ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={<Megaphone size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((campaign) => (
            <li key={campaign.id}>
              <button
                type="button"
                onClick={() => setOpen(campaign)}
                className="border-trait bg-carte hover:bg-poudre rounded-card flex min-h-16 w-full items-center gap-3 border p-3 text-left"
              >
                {campaign.channel === "email" ? (
                  <EnvelopeSimple aria-hidden size={24} className="text-hibiscus" />
                ) : (
                  <WhatsappLogo aria-hidden size={24} className="text-hibiscus" />
                )}
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate font-bold">{campaign.name}</span>
                  <span className="text-small text-prune-doux">{tSegment(campaign.segment)}</span>
                </span>
                <span className="text-small shrink-0 font-bold">
                  {campaign.stats ? t("sentCount", { count: campaign.stats.sent }) : t("draft")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {creating && <EditSheet onClose={() => setCreating(false)} />}
      {open && <CampaignSheet campaign={open} locale={locale} onClose={() => setOpen(null)} />}
    </div>
  );
}

function EditSheet({ onClose }: { onClose: () => void }) {
  const t = useTranslations("glowpro.campaigns");
  const tSegment = useTranslations("glowpro.segments");
  const toast = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [segment, setSegment] = useState<Segment>("inactive");
  const [days, setDays] = useState("60");
  const [channel, setChannel] = useState<"email" | "whatsapp">("email");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await addCampaign({
        name,
        segment,
        inactive_days: Number(days) || 60,
        channel,
        subject,
        body,
      });
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      toast(t("saved"), "success");
      onClose();
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open onOpenChange={(value) => !value && onClose()} title={t("new")}>
      <div className="flex flex-col gap-4">
        <Input
          label={t("name")}
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">{t("who")}</legend>
          {SEGMENTS.map((value) => (
            <label key={value} className="flex min-h-12 items-center gap-3">
              <input
                type="radio"
                name="segment"
                className="accent-hibiscus size-6"
                checked={segment === value}
                onChange={() => setSegment(value)}
              />
              {tSegment(value)}
            </label>
          ))}
        </fieldset>
        {segment === "inactive" && (
          <Input
            label={t("days")}
            inputMode="numeric"
            value={days}
            onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))}
          />
        )}
        <div role="radiogroup" aria-label={t("channel")} className="grid grid-cols-2 gap-2">
          {(["email", "whatsapp"] as const).map((value) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={channel === value}
              onClick={() => setChannel(value)}
              className={cn(
                "flex min-h-12 items-center justify-center gap-2 rounded-full border-2 font-bold",
                channel === value ? "border-hibiscus bg-poudre" : "border-trait",
              )}
            >
              {value === "email" ? (
                <EnvelopeSimple aria-hidden size={22} />
              ) : (
                <WhatsappLogo aria-hidden size={22} />
              )}
              {value === "email" ? t("email") : t("whatsapp")}
            </button>
          ))}
        </div>
        {channel === "email" && (
          <Input
            label={t("subject")}
            value={subject}
            maxLength={120}
            onChange={(e) => setSubject(e.target.value)}
          />
        )}
        <label className="flex flex-col gap-2 font-bold">
          {t("message")}
          <textarea
            rows={5}
            maxLength={1000}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="border-trait bg-carte rounded-[14px] border-2 p-3 font-normal"
          />
          <span className="text-small text-prune-doux font-normal">{t("messageHelp")}</span>
        </label>
        <Button
          size="lg"
          fullWidth
          disabled={busy || !name.trim() || !body.trim()}
          onClick={() => void save()}
        >
          {t("saveDraft")}
        </Button>
      </div>
    </Sheet>
  );
}

function CampaignSheet({
  campaign,
  locale,
  onClose,
}: {
  campaign: Campaign;
  locale: string;
  onClose: () => void;
}) {
  const t = useTranslations("glowpro.campaigns");
  const toast = useToast();
  const queryClient = useQueryClient();
  const audience = useQuery({
    queryKey: ["campaign-audience", campaign.id],
    queryFn: () => getAudience(campaign.id),
    enabled: campaign.status === "draft",
  });
  const [busy, setBusy] = useState(false);
  const stats = campaign.stats;

  const send = async () => {
    setBusy(true);
    try {
      await sendCampaign(campaign.id);
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      toast(t("sent"), "success");
      onClose();
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open onOpenChange={(value) => !value && onClose()} title={campaign.name}>
      <div className="flex flex-col gap-4">
        <p className="bg-poudre rounded-2xl p-3 whitespace-pre-line">{campaign.body}</p>
        {stats ? (
          <dl className="grid grid-cols-2 gap-3">
            {(
              [
                ["sent", stats.sent],
                ["failed", stats.failed],
                ["withoutConsent", stats.without_consent],
                ["unsubscribed", stats.unsubscribed],
                ["returned", stats.returned],
                ["pending", stats.pending],
              ] as const
            ).map(([key, value]) => (
              <div key={key} className="border-trait rounded-2xl border p-3">
                <dt className="text-small text-prune-doux">{t(`stats.${key}`)}</dt>
                <dd className="text-title font-bold">{value}</dd>
              </div>
            ))}
            {campaign.sent_at && (
              <p className="text-small text-prune-doux col-span-2">
                {t("sentOn", {
                  date: new Intl.DateTimeFormat(locale, { day: "numeric", month: "long" }).format(
                    new Date(campaign.sent_at),
                  ),
                })}
              </p>
            )}
          </dl>
        ) : audience.data ? (
          <>
            <p className="font-bold">{t("audience", { count: audience.data.recipients })}</p>
            <p className="text-small text-prune-doux">
              {t("withoutConsent", { count: audience.data.without_consent })}
            </p>
            {audience.data.limit !== null && (
              <p className="text-small text-prune-doux">
                {t("monthly", { used: audience.data.sent_this_month, limit: audience.data.limit })}
              </p>
            )}
            <Button size="lg" fullWidth disabled={busy} onClick={() => void send()}>
              <PaperPlaneTilt aria-hidden size={24} weight="bold" />
              {t("send", { count: audience.data.recipients })}
            </Button>
          </>
        ) : (
          <Skeleton className="h-20 rounded-2xl" />
        )}
      </div>
    </Sheet>
  );
}
