import {
  CalendarCheck,
  ChatCircleText,
  Clock,
  DoorOpen,
  Gift,
  Key,
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
  Trash,
  Van,
  UserCheck,
  UserPlus,
  Waveform,
  WhatsappLogo,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { TradeLabel } from "@/components/features/trades/trade-label";
import { TRADES, type Trade } from "@/components/features/trades/trade-icon";
import { Avatar } from "@/components/ui/avatar";
import { ProLevelBadge } from "@/components/features/games/glow-bits";
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
import { mediaSrc, mediaSrcSet, voiceSrc } from "@/lib/media";
import { preloadMainPicture } from "@/lib/media-preload";
import {
  durationParts,
  formatClock,
  formatMoment,
  weekdayIn,
  weekdayName,
} from "@/lib/pros/format";

import { MapPreview } from "./map-preview";
import { ArrivalButton, RemovePreparedPage, ShowcaseActions } from "./showcase-actions";

// Downloaded only when the page has a video (ADR-004).
const VideoPlayer = dynamic(() => import("./video-player").then((m) => m.VideoPlayer));

const isTrade = (key: string): key is Trade => (TRADES as readonly string[]).includes(key);

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <h2 id={id} className="font-display text-title">
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

function ServiceRow({
  service,
  slug,
  bookable,
}: {
  service: Service;
  slug: string;
  bookable: boolean;
}) {
  const t = useTranslations("pros.showcase");
  const duration = durationParts(service.duration_minutes);
  return (
    <li className="border-trait flex flex-col gap-2 border-b py-4 last:border-b-0">
      <div className="flex items-start justify-between gap-3">
        <span className="text-lead font-semibold">{service.name}</span>
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
      {bookable && (
        <Link
          href={`/${slug}/rdv?service=${service.id}`}
          className={buttonClasses({ variant: "secondary", className: "self-start lg:self-end" })}
        >
          <CalendarCheck aria-hidden size={22} />
          {t("bookService")}
        </Link>
      )}
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
  const COVER_SIZES = "(min-width: 1024px) 66vw, 100vw";
  const coverSet = mediaSrcSet(showcase.cover);
  preloadMainPicture(showcase.cover, COVER_SIZES);
  // Beside the cover, the work itself, when it is a photo.
  const works = showcase.portfolio
    .filter((item) => item.media.kind !== "video")
    .map((item) => mediaSrc(item.media, "large", "medium"))
    .filter((src): src is string => !!src && src !== cover);
  const pictures = (cover ? [cover, ...works] : works).slice(0, 3);
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
  // Prepared by the team before the professional took the page: clients write to them on
  // WhatsApp (no online booking), and the page says who did the work.
  const prepared = showcase.prepared;
  const whatsappHref = prepared?.whatsapp
    ? `https://wa.me/${prepared.whatsapp}?text=${encodeURIComponent(
        t("prepared.whatsappText", { name }),
      )}`
    : null;

  return (
    <article className="flex flex-col gap-10">
      {showcase.status !== "published" && (
        <div className="bg-poudre rounded-card flex flex-col items-start gap-2 p-4" role="status">
          <p className="font-bold">{t("previewTitle")}</p>
          <p className="text-prune-doux">{t("previewText")}</p>
          <Link href="/pro/ma-page" className={buttonClasses({ variant: "secondary" })}>
            <NotePencil aria-hidden size={22} weight="bold" />
            {t("previewEdit")}
          </Link>
        </div>
      )}

      {prepared && (
        <section
          aria-labelledby="prepared-title"
          className="border-trait rounded-card flex flex-col items-start gap-3 border-2 p-4"
        >
          <h2 id="prepared-title" className="font-bold">
            {t("prepared.title")}
          </h2>
          <p>{t("prepared.text", { name })}</p>
          <div className="flex flex-wrap gap-3">
            {whatsappHref && (
              <a
                href={whatsappHref}
                target="_blank"
                rel="noopener noreferrer"
                className={buttonClasses({ variant: "secondary" })}
              >
                <WhatsappLogo aria-hidden size={22} weight="bold" />
                {t("prepared.whatsapp")}
              </a>
            )}
            <Link
              href={{ pathname: "/auth", query: { mode: "forgot" } }}
              className={buttonClasses({ variant: "quiet" })}
            >
              <Key aria-hidden size={22} weight="bold" />
              {t("prepared.claim")}
            </Link>
          </div>
          <RemovePreparedPage
            slug={showcase.slug}
            name={name}
            icon={<Trash aria-hidden size={22} weight="bold" />}
          />
        </section>
      )}

      <header
        className={`flex flex-col gap-5 ${
          pictures.length === 1
            ? "lg:grid lg:grid-cols-[22rem_minmax(0,1fr)] lg:items-end lg:gap-x-8"
            : ""
        }`}
      >
        {pictures.length > 0 && (
          <div
            className={`rounded-card grid aspect-[4/3] grid-cols-1 gap-1 overflow-clip ${
              pictures.length === 1
                ? "lg:row-span-2 lg:aspect-[4/5]"
                : "lg:aspect-auto lg:h-[26rem] lg:grid-cols-[2fr_1fr] lg:grid-rows-2"
            }`}
          >
            {pictures.map((src, index) => (
              // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
              <img
                key={src}
                src={src}
                alt=""
                srcSet={index === 0 && cover ? coverSet : undefined}
                sizes={index === 0 && cover && coverSet ? COVER_SIZES : undefined}
                fetchPriority={index === 0 ? "high" : undefined}
                loading={index === 0 ? undefined : "lazy"}
                className={`bg-poudre size-full min-h-0 object-cover object-[50%_20%] ${
                  index > 0 ? "max-lg:hidden" : ""
                } ${pictures.length === 2 || (index === 0 && pictures.length === 3) ? "lg:row-span-2" : ""}`}
              />
            ))}
          </div>
        )}
        <div className="flex items-center gap-4">
          <Avatar name={name} src={photo} size="md" className="shrink-0" />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <div className="flex items-start gap-2">
              <h1 className="font-display text-headline lg:text-display min-w-0">{name}</h1>
              <SpeakButton text={[name, showcase.bio].filter(Boolean).join(". ")} />
            </div>
            <ul className="flex flex-wrap gap-x-4 gap-y-1">
              {showcase.trades
                .filter((trade) => isTrade(trade.key))
                .map((trade) => (
                  <li key={trade.key}>
                    <TradeLabel trade={trade.key as Trade} className="font-semibold" />
                  </li>
                ))}
            </ul>
          </div>
        </div>
        <div className="text-small flex flex-wrap items-center gap-x-4 gap-y-2">
          {showcase.verified && <Badge tone="verified">{t("verified")}</Badge>}
          {showcase.trained && <Badge tone="trained">{t("trained")}</Badge>}
          <ProLevelBadge level={showcase.level} />
          <span className="inline-flex items-center gap-1">
            <Star aria-hidden size={18} weight="fill" />
            {showcase.rating_count > 0 && showcase.rating_average !== null
              ? t("rating", {
                  rating: showcase.rating_average.toLocaleString(locale, {
                    maximumFractionDigits: 1,
                  }),
                  count: showcase.rating_count,
                })
              : t("noReviews")}
          </span>
          <span className="inline-flex items-center gap-1">
            <MapPin aria-hidden size={18} />
            {[place.district, place.city].filter(Boolean).join(", ")}
          </span>
        </div>
      </header>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-12">
        <aside className="lg:bg-poudre lg:rounded-card order-first flex flex-col gap-3 self-start lg:sticky lg:top-20 lg:order-last lg:p-4">
          <OpeningLine showcase={showcase} />
          {whatsappHref && (
            <a
              href={whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonClasses({ size: "lg", fullWidth: true, className: "max-lg:hidden" })}
            >
              <WhatsappLogo aria-hidden size={26} weight="bold" />
              {t("prepared.whatsapp")}
            </a>
          )}
          <ShowcaseActions
            bookable={!prepared}
            name={name}
            slug={showcase.slug}
            shortLink={showcase.short_link}
            directionsUrl={place.directions_url}
            giftable={showcase.services.some(
              (service) =>
                service.price_kind === "fixed" && service.price_minor && service.currency === "XOF",
            )}
            icons={{
              book: <CalendarCheck aria-hidden size={26} weight="bold" />,
              directions: <NavigationArrow aria-hidden size={22} weight="bold" />,
              share: <ShareNetwork aria-hidden size={22} weight="bold" />,
              gift: <Gift aria-hidden size={22} weight="bold" />,
            }}
          />
          {!prepared && (
            <WriteButton
              personId={showcase.owner_id}
              icon={<ChatCircleText aria-hidden size={22} weight="bold" />}
            />
          )}
          <FollowButton
            userId={showcase.owner_id}
            followed={showcase.followed}
            count={showcase.follower_count}
            icons={{
              follow: <UserPlus aria-hidden size={22} weight="bold" />,
              following: <UserCheck aria-hidden size={22} weight="bold" />,
            }}
          />
        </aside>
        <div className="flex min-w-0 flex-col gap-10">
          <Section id="services" title={t("services")} icon={<Scissors size={26} />}>
            {groups.length === 0 ? (
              <p className="text-prune-doux">{t("noServices")}</p>
            ) : (
              groups.map((group) => (
                <div key={group.key} className="flex flex-col">
                  {group.title && (
                    <h3 className="text-small text-prune-doux font-semibold">{group.title}</h3>
                  )}
                  <ul className="flex flex-col">
                    {group.services.map((service) => (
                      <ServiceRow
                        key={service.id}
                        service={service}
                        slug={showcase.slug}
                        bookable={!prepared}
                      />
                    ))}
                  </ul>
                </div>
              ))
            )}
          </Section>

          {showcase.portfolio.length > 0 && (
            <Section id="portfolio" title={t("portfolio")} icon={<Star size={26} />}>
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
                                className="rounded-photo aspect-[4/5] w-full object-cover"
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
                          className="rounded-photo aspect-[4/5] w-full object-cover"
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
            <Section id="shop" title={t("shop")} icon={<Storefront size={26} />}>
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

          {(showcase.bio || bioVoice) && (
            <Section id="about" title={t("about")} icon={<SealCheck size={26} />}>
              {showcase.bio && <p className="whitespace-pre-line">{showcase.bio}</p>}
              {bioVoice && (
                <div className="flex flex-col gap-2">
                  <p className="text-small flex items-center gap-1 font-bold">
                    <Waveform aria-hidden size={18} />
                    {t("bioVoice")}
                  </p>
                  <audio controls preload="none" src={bioVoice} className="w-full">
                    <track kind="captions" />
                  </audio>
                </div>
              )}
            </Section>
          )}

          {posts.length > 0 && (
            <Section id="posts" title={t("posts")} icon={<Star size={26} />}>
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

          <Section id="hours" title={t("hours")} icon={<Clock size={26} />}>
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

          <Section id="place" title={t("place")} icon={<MapPin size={26} />}>
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
                      <Waveform aria-hidden size={18} />
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
            {showcase.other_places.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="font-bold">{t("otherPlaces")}</p>
                <ul className="flex flex-col gap-2">
                  {showcase.other_places.map((other) => (
                    <li key={other.id}>
                      <span className="block font-semibold">{other.name}</span>
                      <span className="text-prune-doux block">
                        {[other.address, other.district, other.city].filter(Boolean).join(", ")}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {travel.travels_to_clients && (
              <div className="bg-poudre rounded-card flex flex-col gap-1 p-4">
                <p className="flex items-center gap-2 font-bold">
                  <Van aria-hidden size={22} />
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
            <Section id="more" title={t("more")} icon={<Globe size={26} />}>
              {showcase.languages.length > 0 && (
                <p className="flex flex-wrap items-center gap-2">
                  <Translate aria-hidden size={20} />
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
        </div>
      </div>
      {whatsappHref && (
        <div className="bg-carte border-trait pb-safe fixed inset-x-0 bottom-0 z-40 border-t p-3 lg:hidden">
          <a
            href={whatsappHref}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses({ size: "lg", fullWidth: true })}
          >
            <WhatsappLogo aria-hidden size={26} weight="bold" />
            {t("prepared.whatsapp")}
          </a>
        </div>
      )}
      {!prepared && showcase.slug && showcase.status === "published" && (
        <div className="bg-carte border-trait pb-safe fixed inset-x-0 bottom-0 z-40 border-t p-3 lg:hidden">
          <Link
            href={`/${showcase.slug}/rdv`}
            className={buttonClasses({ size: "lg", fullWidth: true })}
          >
            <CalendarCheck aria-hidden size={26} weight="bold" />
            {t("bookSticky")}
          </Link>
        </div>
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
