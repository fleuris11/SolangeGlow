import { Megaphone, SealCheck, Star } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import { buttonClasses } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import type { Ad, AdList } from "@/lib/api/ads";
import { cn } from "@/lib/cn";
import { mediaSrc } from "@/lib/media";

import { AdSense } from "./adsense-loader";

/** « Sponsored », always visible on an ad: the icon and the word (never colour alone). */
export function SponsoredLabel({ ad, className }: { ad: Ad; className?: string }) {
  const t = useTranslations("ads");
  return (
    <p
      className={cn(
        "text-mention text-prune-doux inline-flex items-center gap-1 font-bold",
        className,
      )}
    >
      <Megaphone aria-hidden size={16} weight="fill" />
      {ad.house ? t("house") : t("sponsoredBy", { name: ad.sponsor })}
    </p>
  );
}

function Picture({ ad, className }: { ad: Ad; className?: string }) {
  const first = ad.media[0] ?? ad.pro?.photo ?? ad.product?.photo ?? null;
  if (!first) return null;
  if (first.kind === "video") {
    return (
      <video
        controls
        preload="none"
        playsInline
        poster={mediaSrc(first, "medium")}
        className={cn("rounded-photo bg-poudre w-full", className)}
      >
        <source src={first.urls.low ?? first.urls.medium} type="video/mp4" />
      </video>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
    <img
      src={mediaSrc(first, "medium", "large")}
      alt=""
      loading="lazy"
      className={cn("rounded-photo bg-poudre aspect-[4/3] w-full object-cover", className)}
    />
  );
}

function Cta({ ad, label }: { ad: Ad; label: string }) {
  return (
    <a href={ad.click_url} rel="sponsored" className={buttonClasses({ className: "self-start" })}>
      {ad.cta || label}
    </a>
  );
}

/** The banner at the top of the home page. */
export function AdBanner({ ad }: { ad: Ad }) {
  const t = useTranslations("ads");
  return (
    <aside aria-label={t("aria")} className="bg-poudre rounded-card flex flex-col gap-3 p-4">
      <SponsoredLabel ad={ad} />
      <Picture ad={ad} />
      {ad.title && <p className="text-lead font-bold">{ad.title}</p>}
      {ad.text && <p>{ad.text}</p>}
      <Cta ad={ad} label={t("discover")} />
    </aside>
  );
}

/** A sponsored post of the feed: a picture, a short video, a carousel or a pro. */
export function SponsoredPost({ ad }: { ad: Ad }) {
  const t = useTranslations("ads");
  const carousel = ad.format === "carousel" && ad.media.length > 1;
  return (
    <article
      aria-label={t("aria")}
      className="border-trait bg-carte rounded-card flex flex-col gap-3 border p-4"
    >
      <SponsoredLabel ad={ad} />
      {ad.pro && <ProLine ad={ad} />}
      {carousel ? (
        <ul className="flex snap-x gap-2 overflow-x-auto">
          {ad.media.map((media) => (
            <li key={media.id} className="w-4/5 shrink-0 snap-start">
              {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
              <img
                src={mediaSrc(media, "medium", "large")}
                alt=""
                loading="lazy"
                className="rounded-photo bg-poudre aspect-square w-full object-cover"
              />
            </li>
          ))}
        </ul>
      ) : (
        <Picture ad={ad} />
      )}
      {ad.title && !ad.pro && <p className="text-lead font-bold">{ad.title}</p>}
      {ad.text && <p>{ad.text}</p>}
      <Cta ad={ad} label={ad.pro ? t("seeShowcase") : t("discover")} />
    </article>
  );
}

function ProLine({ ad }: { ad: Ad }) {
  const t = useTranslations("ads");
  const locale = useLocale();
  const pro = ad.pro!;
  return (
    <span className="flex min-w-0 flex-col gap-1">
      <span className="text-lead inline-flex items-center gap-1 font-bold">
        <span className="truncate">{pro.name}</span>
        {pro.verified && (
          <SealCheck
            weight="fill"
            size={20}
            className="text-feuille shrink-0"
            aria-label={t("verified")}
          />
        )}
      </span>
      <span className="text-small text-prune-doux">
        {[pro.trades.map((trade) => trade.name).join(", "), pro.city].filter(Boolean).join(" — ")}
      </span>
      {pro.rating_average !== null && pro.rating_count > 0 && (
        <span className="text-small inline-flex items-center gap-1">
          <Star aria-hidden size={16} weight="fill" className="text-or" />
          {t("rating", {
            average: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(
              pro.rating_average,
            ),
            count: pro.rating_count,
          })}
        </span>
      )}
    </span>
  );
}

/** A pro shown first in the search (a boost or a campaign), marked « Sponsored ». */
export function SponsoredPro({ ad }: { ad: Ad }) {
  const t = useTranslations("ads");
  if (!ad.pro) return <SponsoredPost ad={ad} />;
  return (
    <a
      href={ad.click_url}
      rel="sponsored"
      aria-label={t("proAria", { name: ad.pro.name })}
      className="border-or bg-carte rounded-card flex items-center gap-3 border-2 p-3"
    >
      <Avatar name={ad.pro.name} src={mediaSrc(ad.pro.photo, "thumb", "medium")} size="lg" />
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <SponsoredLabel ad={ad} />
        <ProLine ad={ad} />
      </span>
    </a>
  );
}

/** A sponsored product (a shop of a pro, or the France Selection). */
export function SponsoredProduct({ ad }: { ad: Ad }) {
  const t = useTranslations("ads");
  if (!ad.product) return <SponsoredPost ad={ad} />;
  return (
    <a
      href={ad.click_url}
      rel="sponsored"
      aria-label={t("productAria", { name: ad.product.title })}
      className="border-trait bg-carte rounded-card flex items-center gap-3 border p-3"
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
      <img
        src={mediaSrc(ad.product.photo, "thumb", "medium")}
        alt=""
        loading="lazy"
        width={80}
        height={80}
        className="rounded-photo bg-poudre size-20 shrink-0 object-cover"
      />
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <SponsoredLabel ad={ad} />
        <span className="font-bold">{ad.product.title}</span>
        <span className="text-small text-prune-doux">{ad.product.seller}</span>
        <PriceTag amountMinor={ad.product.price_minor} currency={ad.product.currency} />
      </span>
    </a>
  );
}

/** The ad of a placement, or the AdSense filler when it is set, or nothing. */
export function AdSlot({ list }: { list: AdList | null }) {
  if (!list) return null;
  const ad = list.results[0];
  if (!ad) {
    return list.adsense ? <AdSense client={list.adsense.client} slot={list.adsense.slot} /> : null;
  }
  if (ad.placement === "search") return <SponsoredPro ad={ad} />;
  if (ad.placement === "product") return <SponsoredProduct ad={ad} />;
  if (ad.placement === "home_banner") return <AdBanner ad={ad} />;
  return <SponsoredPost ad={ad} />;
}
