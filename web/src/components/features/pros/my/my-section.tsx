"use client";

import dynamic from "next/dynamic";
import { useEffect, type ComponentType } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import type { MyPro } from "@/lib/api/pros";
import { useMe } from "@/lib/auth/use-me";
import { useRouter } from "@/lib/i18n/navigation";
import { useMyPro } from "@/lib/pros/use-my-pro";

import type { Section } from "./sections";

const loading = () => <Skeleton className="rounded-card h-96" />;

// Each part is downloaded only when opened.
const PARTS: Record<Section, ComponentType<{ pro: MyPro }>> = {
  info: dynamic(() => import("./info-section").then((m) => m.InfoSection), { loading }),
  services: dynamic(() => import("./services-section").then((m) => m.ServicesSection), {
    loading,
  }),
  hours: dynamic(() => import("./hours-section").then((m) => m.HoursSection), { loading }),
  portfolio: dynamic(() => import("./portfolio-section").then((m) => m.PortfolioSection), {
    loading,
  }),
  reviews: dynamic(() => import("./reviews-part").then((m) => m.ReviewsPart), { loading }),
  messages: dynamic(() => import("./messages-part").then((m) => m.MessagesPart), { loading }),
  place: dynamic(() => import("./place-section").then((m) => m.PlaceSection), { loading }),
  share: dynamic(() => import("./share-section").then((m) => m.ShareSection), { loading }),
  verification: dynamic(() => import("./verification-section").then((m) => m.VerificationSection), {
    loading,
  }),
};

export function MySection({ section }: { section: Section }) {
  const router = useRouter();
  const me = useMe();
  const pro = useMyPro();

  useEffect(() => {
    if (me.data === null) router.replace("/auth");
    else if (pro.data === null) router.replace("/pro/start");
  }, [me.data, pro.data, router]);

  if (!pro.data) return loading();
  const Part = PARTS[section];
  return <Part pro={pro.data} />;
}
