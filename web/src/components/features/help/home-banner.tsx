import { useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import type { Schemas } from "@/lib/api/client";
import { mediaSrc } from "@/lib/media";

/** The banner written by the team, at the top of the home page (module 12). */
export function HomeBanners({ banners }: { banners: Schemas["Banner"][] }) {
  const t = useTranslations("help.banner");
  if (banners.length === 0) return null;
  return (
    <>
      {banners.map((banner) => (
        <aside
          key={banner.id}
          aria-label={t("aria")}
          className="border-trait rounded-card bg-carte flex flex-col gap-3 border p-4"
        >
          {banner.image && (
            // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
            <img
              src={mediaSrc(banner.image, "medium", "large")}
              alt=""
              className="rounded-photo bg-poudre aspect-[16/7] w-full object-cover"
            />
          )}
          <p className="text-lead font-bold">{banner.title}</p>
          {banner.text && <p>{banner.text}</p>}
          {banner.link && (
            <a href={banner.link} className={buttonClasses({ className: "self-start" })}>
              {banner.cta || t("discover")}
            </a>
          )}
        </aside>
      ))}
    </>
  );
}
