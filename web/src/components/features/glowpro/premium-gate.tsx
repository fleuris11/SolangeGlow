"use client";

import { Crown, Sparkle } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api/client";
import { getMyGlowPro, startTrial, type GlowFeature } from "@/lib/api/glowpro";
import { Link } from "@/lib/i18n/navigation";

export const GLOWPRO_KEY = ["glowpro"];

/** The pro's plan, shared by every Glow Pro screen. */
export function useGlowPro() {
  const query = useQuery({ queryKey: GLOWPRO_KEY, queryFn: getMyGlowPro, retry: false });
  const features = query.data?.current.features ?? [];
  return { ...query, has: (feature: GlowFeature) => features.includes(feature) };
}

/** « Part of Premium »: what it brings, and the free trial in one tap. */
export function PremiumOffer({ title, text }: { title: string; text?: string }) {
  const t = useTranslations("glowpro.gate");
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data } = useGlowPro();
  const [busy, setBusy] = useState(false);
  const premium = data?.plans.find((plan) => !plan.is_default);
  const canTry = !!premium && !data?.subscription.trial_used && premium.trial_days > 0;

  const tryIt = async () => {
    setBusy(true);
    try {
      await startTrial();
      await queryClient.invalidateQueries();
      toast(t("trialStarted"), "success");
    } catch (caught) {
      toast(caught instanceof ApiError ? caught.message : t("error"), "warning");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="bg-poudre rounded-card flex flex-col gap-3 p-5"
      aria-labelledby="premium-offer"
    >
      <p className="text-small flex items-center gap-2 font-bold">
        <Crown aria-hidden size={22} weight="duotone" className="text-hibiscus" />
        {t("badge")}
      </p>
      <h2 id="premium-offer" className="text-title font-bold">
        {title}
      </h2>
      {text && <p className="text-prune-doux">{text}</p>}
      {canTry ? (
        <Button size="lg" fullWidth disabled={busy} onClick={() => void tryIt()}>
          <Sparkle aria-hidden size={24} weight="bold" />
          {t("try", { days: premium.trial_days })}
        </Button>
      ) : (
        <Link href="/pro/plan" className={buttonClasses({ size: "lg", fullWidth: true })}>
          {t("see")}
        </Link>
      )}
    </section>
  );
}

/** Shows the children with Premium, the offer otherwise. */
export function PremiumGate({
  feature,
  title,
  text,
  children,
}: {
  feature: GlowFeature;
  title: string;
  text?: string;
  children: ReactNode;
}) {
  const { has, isPending } = useGlowPro();
  if (isPending) return null;
  return has(feature) ? <>{children}</> : <PremiumOffer title={title} text={text} />;
}
