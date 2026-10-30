"use client";

import { X } from "@phosphor-icons/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { buttonClasses } from "@/components/ui/button";
import { getAds } from "@/lib/api/ads";
import { mediaSrc } from "@/lib/media";

/** The launch screen: one ad, « Sponsored », « Skip » at once, closes by itself. */
export function SplashAd({ onClose }: { onClose: () => void }) {
  const t = useTranslations("ads");
  const query = useQuery({
    queryKey: ["ads", "splash"],
    queryFn: () => getAds({ placement: "splash" }),
    retry: false,
  });
  const skip = useRef<HTMLButtonElement>(null);
  const [elapsed, setElapsed] = useState(0);
  const ad = query.data?.results[0];
  const left = ad ? (query.data?.splash_seconds ?? 5) - elapsed : null;

  useEffect(() => {
    if (query.isSuccess && !ad) onClose();
  }, [query.isSuccess, ad, onClose]);

  useEffect(() => {
    if (!ad) return;
    skip.current?.focus();
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    const escape = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", escape);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("keydown", escape);
    };
  }, [ad, onClose]);

  useEffect(() => {
    if (left !== null && left <= 0) onClose();
  }, [left, onClose]);

  if (!ad) return null;
  const picture = mediaSrc(ad.media[0] ?? ad.pro?.photo ?? ad.product?.photo, "large", "medium");
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="splash-title"
      className="bg-lait fixed inset-0 z-[70] flex flex-col gap-4 overflow-y-auto p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-mention text-prune-doux font-bold">
          {ad.house ? t("house") : t("sponsoredBy", { name: ad.sponsor })}
        </p>
        <button
          ref={skip}
          type="button"
          onClick={onClose}
          className={buttonClasses({ variant: "secondary" })}
        >
          <X aria-hidden size={20} weight="bold" />
          {left !== null && left > 0 ? t("skipIn", { count: left }) : t("skip")}
        </button>
      </div>
      {picture && (
        // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
        <img src={picture} alt="" className="rounded-photo bg-poudre w-full object-cover" />
      )}
      <h2 id="splash-title" className="font-display text-headline font-black">
        {ad.title || ad.pro?.name || ad.product?.title}
      </h2>
      {ad.text && <p className="text-lead">{ad.text}</p>}
      <a
        href={ad.click_url}
        rel="sponsored"
        className={buttonClasses({ size: "lg", fullWidth: true })}
      >
        {ad.cta || t("discover")}
      </a>
    </div>
  );
}
