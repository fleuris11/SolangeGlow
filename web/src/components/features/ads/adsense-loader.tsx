"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

const SCRIPT_ID = "sg-adsense";

type Window = typeof globalThis & { adsbygoogle?: unknown[] };

/** The Google AdSense filler: loaded only when the owner set it in the admin. */
export function AdSense({ client, slot }: { client: string; slot: string }) {
  const t = useTranslations("ads");
  useEffect(() => {
    if (!document.getElementById(SCRIPT_ID)) {
      const script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.async = true;
      script.crossOrigin = "anonymous";
      script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(client)}`;
      document.head.appendChild(script);
    }
    const target = window as Window;
    target.adsbygoogle = target.adsbygoogle ?? [];
    target.adsbygoogle.push({});
  }, [client]);
  return (
    <aside aria-label={t("aria")} className="flex flex-col gap-2">
      <p className="text-mention text-prune-doux font-bold">{t("sponsored")}</p>
      <ins
        className="adsbygoogle block"
        data-ad-client={client}
        data-ad-slot={slot}
        data-ad-format="auto"
        data-full-width-responsive="true"
      />
    </aside>
  );
}
