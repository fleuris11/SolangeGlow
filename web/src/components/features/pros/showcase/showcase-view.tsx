import {
  CalendarCheck,
  ChatCircleText,
  Clock,
  DoorOpen,
  Gift,
  MapTrifold,
  NavigationArrow,
  ShareNetwork,
  Globe,
  MapPin,
  NotePencil,
  Scissors,
  SealCheck,
  ShoppingBag,
  Star,
  Storefront,
  Translate,
  Van,
  UserCheck,
  UserPlus,
  Waveform,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { buttonClasses } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import { SpeakButton } from "@/components/ui/speak-button";
import { WriteButton } from "@/components/features/messaging/write-button";
import { ProductCard } from "@/components/features/shop/product-card";
import { FollowButton } from "@/components/features/social/follow-button";
import { ReviewsSection } from "@/components/features/social/reviews-section";
import type { Service, Showcase } from "@/lib/api/pros";
import type { ShopPage } from "@/lib/api/shop";
import type { Post, ReviewPage } from "@/lib/api/social";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, voiceSrc } from "@/lib/media";
import {
  durationParts,
  formatClock,
  formatMoment,
  weekdayIn,
  weekdayName,
} from "@/lib/pros/format";

import { MapPreview } from "./map-preview";
import { ArrivalButton, ShowcaseActions } from "./showcase-actions";

// Downloaded only when the page has a video (ADR-004).
const VideoPlayer = dynamic(() => import("./video-player").then((m) => m.VideoPlayer));

const isTrade = (key: string): key is Trade => (TRADES as readonly string[]).includes(key);

function Section({
  id,
  title,
  icon,
  children,
}: {
  id: string;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <h2 id={id} className="text-title flex items-center gap-2 font-bold">
        <span aria-hidden className="text-hibiscus inline-flex">
          {icon}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

function OpeningLine({ showcase }: { showcase: Showcase }) {
  const t = useTranslations("pros.showcase");
  const locale = useLocale();
  const { opening } = showcase;
  let text: string;
  if (!opening.has_hours) text = t("noHours");
  else if (opening.is_open && opening.closes_at)
    text = t("openUntil", { time: formatMoment(opening.closes_at, opening.time_zone, locale) });
  else if (opening.closed_today && !opening.next_opening) text = t("closedToday");
  else if (opening.next_opening)
    text = t("closedOpens", {
      when: formatMoment(opening.next_opening, opening.time_zone, locale),
    });
  else text = t("closed");
  return (
    <p className="flex items-center gap-2 font-bold">
      <span
        aria-hidden
        className={`size-3 shrink-0 rounded-full ${opening.is_open ? "bg-feuille" : "bg-prune-doux"}`}
      />
      <Clock aria-hidden size={20} className="text-prune-doux" />
      {text}
    </p>
  );
}

function ServiceRow({ service, slug }: { service: Service; slug: string }) {
  const t = useTranslations("pros.showcase");
  const duration = durationParts(service.duration_minutes);
  return (
    <li className="border-trait flex flex-col gap-2 border-b py-4 last:border-b-0">
      <div className="flex items-start justify-between gap-3">
        <span className="text-lead font-bold">{service.name}</span>
        {service.price_kind === "quote" || service.price_minor === null ? (
          <span className="font-bold whitespace-nowrap">{t("quote")}</span>
        ) : (
          <PriceTag
            amountMinor={service.price_minor}
            currency={service.currency}
            prefix={service.price_kind === "from" ? t("priceFrom") : undefined}
          />
        )}
      </div>
      <p className="text-small text-prune-doux flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="inline-flex items-center gap-1">
          <Clock aria-hidden size={16} />
          {t("duration", duration)}
        </span>
        {service.waiting_minutes > 0 && (
          <span>{t("waiting", { minutes: service.waiting_minutes })}</span>
        )}
        {service.available_at_home && (
          <span className="inline-flex items-center gap-1">
            <Van aria-hidden size={16} />
            {t("atHome")}
          </span>
        )}
      </p>
      {service.description && <p className="text-prune-doux">{service.description}</p>}
      {service.options.length > 0 && (
        <ul className="text-small flex flex-col gap-1">
          {service.options.map((option) => (
            <li key={option.name} className="flex justify-between gap-3">
              <span>{t("option", { name: option.name })}</span>
              {(option.price_minor ?? 0) > 0 && (
                <PriceTag amountMinor={option.price_minor ?? 0} currency={service.currency} />
              )}
            </li>
          ))}
        </ul>
      )}
      <Link
        href={`/${slug}/rdv?service=${service.id}`}
        className={buttonClasses({ variant: "secondary", className: "self-start" })}
      >
        <CalendarCheck aria-hidden size={22} />
        {t("bookService")}
      </Link>
    </li>
  );
}

/** The public page of a pro: her site, the one she shares on her networks. */
export function ShowcaseView({
  showcase,
  reviews = null,
  posts = [],
  shop = null,
}: {
  showcase: Showcase;
  reviews?: ReviewPage | null;
  posts?: Post[];
  shop?: ShopPage | null;
}) {
  const t = useTranslations("pros.showcase");
  const locale = useLocale();
  const name = showcase.business_name;
  const photo = mediaSrc(showcase.photo, "medium", "large");
  const cover = mediaSrc(showcase.cover, "large", "medium");
  const bioVoice = voiceSrc(showcase.bio_voice);
  const place = showcase.place;
  const travel = showcase.travel;
  const today = weekdayIn(showcase.opening.time_zone);
  const uncategorised = showcase.services.filter((service) => !service.category_id);
  const groups = [
    ...showcase.categories.map((category) => ({
      key: category.id,
      title: category.name,
      services: showcase.services.filter((service) => service.category_id === category.id),
    })),
    ...(uncategorised.length ? [{ key: "other", title: "", services: uncategorised }] : []),
  ].filter((group) => group.services.length > 0);

  return (
    <article className="flex flex-col gap-10">
      {showcase.status !== "published" && (
        <div className="bg-poudre rounded-card flex flex-col items-start gap-2 p-4" role="status">
          <p className="font-bold">{t("previewTitle")}</p>
          <p className="text-prune-doux">{t("previewText")}</p>
          <Link href="/pro" className={buttonClasses({ variant: "secondary" })}>
            <NotePencil aria-hidden size={22} weight="bold" />
            {t("previewEdit")}
          </Link>
        </div>
      )}

      <header className="flex flex-col gap-4">
        {cover && (
          // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
          <img
            src={cover}
            alt=""
            className="rounded-card -mb-16 aspect-[16/7] w-full object-cover"
            fetchPriority="high"
          />
        )}
        <div className="flex items-end gap-4">
          <Avatar name={name} src={photo} size="xl" className={cover ? "relative" : undefined} />
          <SpeakButton text={[name, showcase.bio].filter(Boolean).join(". ")} />
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="font-display text-display font-black">{name}</h1>
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {showcase.trades
              .filter((trade) => isTrade(trade.key))
              .map((trade) => (
                <li key={trade.key}>
                  <TradeLabel trade={trade.key as Trade} className="font-bold" />
                </li>
              ))}
          </ul>
          <div className="flex flex-wrap items-center gap-3">
            {showcase.verified && <Badge tone="verified">{t("verified")}</Badge>}
            {showcase.trained && <Badge tone="trained">{t("trained")}</Badge>}
            <span className="text-small inline-flex items-center gap-1">
              <Star aria-hidden size={18} weight="fill" className="text-or" />
              {showcase.rating_count > 0 && showcase.rating_average !== null
                ? t("rating", {
                    rating: showcase.rating_average.toLocaleString(locale, {
                      maximumFractionDigits: 1,
                    }),
                    count: showcase.rating_count,
                  })
                : t("noReviews")}
            </span>
          </div>
          <p className="text-prune-doux flex items-center gap-1">
            <MapPin aria-hidden size={18} />
            {[place.district, place.city].filter(Boolean).join(", ")}
          </p>
          <OpeningLine showcase={showcase} />
          <FollowButton
            userId={showcase.owner_id}
            followed={showcase.followed}
            count={showcase.follower_count}
            icons={{
              follow: <UserPlus aria-hidden size={22} weight="bold" />,
              following: <UserCheck aria-hidden size={22} weight="bold" />,
            }}
          />
          <WriteButton
            personId={showcase.owner_id}
            icon={<ChatCircleText aria-hidden size={22} weight="bold" />}
          />
        </div>
        <ShowcaseActions
          name={name}
          slug={showcase.slug}
          shortLink={showcase.short_link}
          directionsUrl={place.directions_url}
          icons={{
            book: <CalendarCheck aria-hidden size={26} weight="bold" />,
            directions: <NavigationArrow aria-hidden size={22} weight="bold" />,
            share: <ShareNetwork aria-hidden size={22} weight="bold" />,
          }}
        />
      </header>

      {(showcase.bio || bioVoice) && (
        <Section id="about" title={t("about")} icon={<SealCheck size={26} weight="duotone" />}>
          {showcase.bio && <p className="whitespace-pre-line">{showcase.bio}</p>}
          {bioVoice && (
            <div className="flex flex-col gap-2">
              <p className="text-small flex items-center gap-1 font-bold">
                <Waveform aria-hidden size={18} className="text-hibiscus" />
                {t("bioVoice")}
              </p>
              <audio controls preload="none" src={bioVoice} className="w-full">
                <track kind="captions" />
              </audio>
            </div>
          )}
        </Section>
      )}

      <Section id="services" title={t("services")} icon={<Scissors size={26} weight="duotone" />}>
        {groups.length === 0 ? (
          <p className="text-prune-doux">{t("noServices")}</p>
        ) : (
          groups.map((group) => (
            <div key={group.key} className="flex flex-col">
              {group.title && (
                <h3 className="text-lead text-prune-doux font-bold">{group.title}</h3>
              )}
              <ul className="flex flex-col">
                {group.services.map((service) => (
                  <ServiceRow key={service.id} service={service} slug={showcase.slug} />
                ))}
              </ul>
            </div>
          ))
        )}
      </Section>

      {showcase.portfolio.length > 0 && (
        <Section id="portfolio" title={t("portfolio")} icon={<Star size={26} weight="duotone" />}>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {showcase.portfolio.map((item) => {
              const after = mediaSrc(item.media, "medium", "large");
              const before = mediaSrc(item.before, "medium", "large");
              const isVideo = item.media.kind === "video";
              return (
                <li
                  key={item.id}
                  className={`flex flex-col gap-2 ${before || isVideo ? "col-span-2" : ""}`}
                >
                  {isVideo ? (
                    <VideoPlayer media={item.media} label={item.caption || name} />
                  ) : before ? (
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        [before, t("before")],
                        [after, t("after")],
                      ].map(([src, label]) => (
                        <figure key={label} className="relative">
                          {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                          <img
                            src={src}
                            alt={`${label} ${item.caption}`.trim()}
                            loading="lazy"
                            className="aspect-[4/5] w-full rounded-2xl object-cover"
                          />
                          <figcaption className="bg-carte text-mention absolute top-2 left-2 rounded-full px-2 py-1 font-bold">
                            {label}
                          </figcaption>
                        </figure>
                      ))}
                    </div>
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                    <img
                      src={after}
                      alt={item.caption || name}
                      loading="lazy"
                      className="aspect-[4/5] w-full rounded-2xl object-cover"
                    />
                  )}
                  {(item.caption || item.service_name) && (
                    <p className="text-small">
                      {item.caption}
                      {item.service_name && (
                        <span className="text-prune-doux block">{item.service_name}</span>
                      )}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      {showcase.slug && showcase.status === "published" && (
        <Link
          href={`/${showcase.slug}/offres`}
          className={buttonClasses({ variant: "secondary", fullWidth: true })}
        >
          <Gift aria-hidden size={22} weight="bold" />
          {t("giftCard")}
        </Link>
      )}

      {shop && shop.products.length > 0 && showcase.slug && (
        <Section id="shop" title={t("shop")} icon={<Storefront size={26} weight="duotone" />}>
          <ul className="grid grid-cols-2 gap-x-3 gap-y-6">
            {shop.products.slice(0, 4).map((product) => (
              <li key={product.id}>
                <ProductCard product={product} shopSlug={showcase.slug as string} />
              </li>
            ))}
          </ul>
          <Link
            href={`/${showcase.slug}/shop`}
            className={buttonClasses({ variant: "secondary", fullWidth: true })}
          >
            <ShoppingBag aria-hidden size={22} weight="bold" />
            {t("shopAll", { count: shop.products.length })}
          </Link>
        </Section>
      )}

      {posts.length > 0 && (
        <Section id="posts" title={t("posts")} icon={<Star size={26} weight="duotone" />}>
          <ul className="grid grid-cols-3 gap-1">
            {posts.slice(0, 9).map((post) => {
              const cover = post.media.find((item) => item.role !== "before") ?? post.media[0];
              return (
                <li key={post.id}>
                  <Link href={`/p/${post.id}`} className="block">
                    {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
                    <img
                      src={mediaSrc(cover?.media, "thumb", "medium")}
                      alt={post.caption || name}
                      loading="lazy"
                      className="bg-poudre aspect-square w-full rounded-xl object-cover"
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Section>
      )}

      {reviews && <ReviewsSection page={reviews} name={name} />}

      <Section id="hours" title={t("hours")} icon={<Clock size={26} weight="duotone" />}>
        {showcase.hours.length === 0 ? (
          <p className="text-prune-doux">{t("noHours")}</p>
        ) : (
          <table className="w-full text-left">
            <caption className="sr-only">{t("hours")}</caption>
            <tbody>
              {Array.from({ length: 7 }, (_, weekday) => {
                const periods = showcase.hours.filter((period) => period.weekday === weekday);
                const isToday = weekday === today;
                return (
                  <tr
                    key={weekday}
                    className={`border-trait border-b last:border-b-0 ${isToday ? "font-bold" : ""}`}
                  >
                    <th scope="row" className="py-3 pr-4 font-bold">
                      {weekdayName(weekday, locale)}
                      {isToday && <span className="sr-only"> ({t("today")})</span>}
                    </th>
                    <td className="py-3 text-right">
                      {periods.length === 0
                        ? t("closed")
                        : periods
                            .map((period) =>
                              t("span", {
                                from: formatClock(period.opens_at, locale),
                                to: formatClock(period.closes_at, locale),
                              }),
                            )
                            .join(", ")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {showcase.closures.length > 0 && (
          <div className="bg-poudre rounded-card flex flex-col gap-1 p-4">
            <p className="font-bold">{t("closures")}</p>
            <ul className="text-small">
              {showcase.closures.map((closure) => (
                <li key={closure.id}>
                  {t("closureRange", {
                    from: new Date(`${closure.starts_on}T12:00:00`),
                    to: new Date(`${closure.ends_on}T12:00:00`),
                  })}
                  {closure.reason ? ` (${closure.reason})` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      <Section id="place" title={t("place")} icon={<MapPin size={26} weight="duotone" />}>
        {place.receives_clients ? (
          <>
            {place.address && <p className="font-bold">{place.address}</p>}
            <p>{[place.district, place.city].filter(Boolean).join(", ")}</p>
            {place.landmarks && (
              <div className="flex flex-col gap-1">
                <p className="font-bold">{t("landmarks")}</p>
                <p className="whitespace-pre-line">{place.landmarks}</p>
              </div>
            )}
            {voiceSrc(place.landmarks_voice) && (
              <div className="flex flex-col gap-2">
                <p className="text-small flex items-center gap-1 font-bold">
                  <Waveform aria-hidden size={18} className="text-hibiscus" />
                  {t("landmarksVoice")}
                </p>
                <audio
                  controls
                  preload="none"
                  src={voiceSrc(place.landmarks_voice)}
                  className="w-full"
                >
                  <track kind="captions" />
                </audio>
              </div>
            )}
            {place.itinerary_video && place.itinerary_video.status === "ready" && (
              <div className="flex flex-col gap-2">
                <p className="font-bold">{t("itineraryVideo")}</p>
                <VideoPlayer media={place.itinerary_video} label={t("itineraryVideo")} />
              </div>
            )}
            {place.latitude !== null && place.longitude !== null && (
              <MapPreview
                name={name}
                latitude={place.latitude}
                longitude={place.longitude}
                country={place.country}
                icon={<MapTrifold aria-hidden size={22} weight="bold" />}
              />
            )}
            {showcase.slug && (
              <ArrivalButton
                slug={showcase.slug}
                name={name}
                icon={<DoorOpen aria-hidden size={24} weight="bold" />}
              />
            )}
          </>
        ) : (
          <p>{t("homeOnly", { name })}</p>
        )}
        {travel.travels_to_clients && (
          <div className="bg-poudre rounded-card flex flex-col gap-1 p-4">
            <p className="flex items-center gap-2 font-bold">
              <Van aria-hidden size={22} className="text-hibiscus" />
              {travel.radius_km ? t("travel", { km: travel.radius_km }) : t("travelArea")}
            </p>
            {(travel.fee_minor ?? 0) > 0 && (
              <p className="text-small">
                {t("travelFee")}{" "}
                <PriceTag amountMinor={travel.fee_minor ?? 0} currency={travel.currency} />
              </p>
            )}
          </div>
        )}
      </Section>

      {(showcase.languages.length > 0 || Object.keys(showcase.social_links).length > 0) && (
        <Section id="more" title={t("more")} icon={<Globe size={26} weight="duotone" />}>
          {showcase.languages.length > 0 && (
            <p className="flex flex-wrap items-center gap-2">
              <Translate aria-hidden size={20} className="text-hibiscus" />
              <span className="font-bold">{t("languages")}</span>
              {showcase.languages.map((language) => language.label).join(", ")}
            </p>
          )}
          <ul className="flex flex-wrap gap-2">
            {Object.entries(showcase.social_links)
              .filter(([network]) => network !== "whatsapp")
              .map(([network, value]) => (
                <li key={network}>
                  <a
                    href={socialHref(network, value)}
                    target="_blank"
                    rel="noopener noreferrer me"
                    className={buttonClasses({ variant: "secondary" })}
                  >
                    {t(`social.${network}` as "social.instagram")}
                  </a>
                </li>
              ))}
          </ul>
        </Section>
      )}
    </article>
  );
}

function socialHref(network: string, value: string): string {
  if (value.startsWith("http")) return value;
  const handle = value.replace(/^@/, "");
  const bases: Record<string, string> = {
    instagram: "https://www.instagram.com/",
    tiktok: "https://www.tiktok.com/@",
    facebook: "https://www.facebook.com/",
    youtube: "https://www.youtube.com/@",
  };
  return (bases[network] ?? "https://") + handle;
}
