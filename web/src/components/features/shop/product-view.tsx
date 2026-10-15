import {
  ArrowLeft,
  BellRinging,
  Heart,
  Hourglass,
  Lightning,
  ShoppingBag,
  Star,
  Waveform,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { SpeakButton } from "@/components/ui/speak-button";
import type { Schemas } from "@/lib/api/client";
import type { ProductDetail } from "@/lib/api/shop";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc, voiceSrc } from "@/lib/media";

import { ProductBuy } from "./buy-buttons";
import { DeliveryInfo } from "./delivery-info";

// Downloaded only when the product has a video (ADR-004).
const VideoPlayer = dynamic(() =>
  import("@/components/features/pros/showcase/video-player").then((m) => m.VideoPlayer),
);

type Reviews = Schemas["ProductReviews"];

/** The product page: photos, price and choices, description (text and voice), delivery, reviews. */
export function ProductView({ product, reviews }: { product: ProductDetail; reviews: Reviews }) {
  const t = useTranslations("shop.product");
  const locale = useLocale();
  const shopSlug = product.shop.slug ?? "";
  const voice = voiceSrc(product.description_voice);

  return (
    <article className="flex flex-col gap-8">
      <Link
        href={`/${shopSlug}/shop`}
        className="text-prune-doux hover:bg-poudre -ml-2 inline-flex min-h-12 items-center gap-2 self-start rounded-full px-2 font-bold"
      >
        <ArrowLeft aria-hidden size={22} />
        {t("back", { name: product.shop.name })}
      </Link>

      <ul
        aria-label={t("photos")}
        // Scrolled with the arrow keys too (keyboard users).
        tabIndex={0}
        className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4"
      >
        {product.photos.map((photo, index) => (
          <li key={photo.id} className="w-[85%] shrink-0 snap-center sm:w-[60%]">
            {/* eslint-disable-next-line @next/next/no-img-element -- resized by the backend */}
            <img
              src={mediaSrc(photo, "large", "medium")}
              alt={index === 0 ? product.title : t("photoN", { n: index + 1 })}
              className="bg-poudre aspect-square w-full rounded-2xl object-cover"
              fetchPriority={index === 0 ? "high" : undefined}
              loading={index === 0 ? undefined : "lazy"}
              width={720}
              height={720}
            />
          </li>
        ))}
      </ul>

      <header className="flex flex-col gap-3">
        {product.category && (
          <p className="text-small text-prune-doux font-bold">{product.category.name}</p>
        )}
        <div className="flex items-start gap-2">
          <h1 className="text-headline flex-1 font-bold">{product.title}</h1>
          <SpeakButton text={[product.title, product.description].filter(Boolean).join(". ")} />
        </div>
        <Link
          href={`/${shopSlug}`}
          className="hover:bg-poudre -ml-2 flex items-center gap-3 self-start rounded-full py-1 pr-4 pl-2"
        >
          <Avatar name={product.shop.name} src={mediaSrc(product.shop.photo, "thumb")} size="sm" />
          <span className="font-bold">{product.shop.name}</span>
          {product.shop.is_verified && <Badge tone="verified">{t("verified")}</Badge>}
        </Link>
      </header>

      <ProductBuy
        product={product}
        locale={locale}
        icons={{
          cart: <ShoppingBag aria-hidden size={26} weight="bold" />,
          heart: <Heart aria-hidden size={22} weight="bold" />,
          heartFilled: <Heart aria-hidden size={22} weight="fill" className="text-hibiscus" />,
          bell: <BellRinging aria-hidden size={24} weight="bold" />,
          flash: <Lightning aria-hidden size={20} weight="fill" />,
        }}
      />

      <p className="flex items-center gap-2">
        <Hourglass aria-hidden size={22} className="text-hibiscus" />
        {product.prep_days > 0 ? t("prep", { count: product.prep_days }) : t("ready")}
      </p>

      {(product.description || voice) && (
        <section aria-labelledby="description" className="flex flex-col gap-3">
          <h2 id="description" className="text-title font-bold">
            {t("description")}
          </h2>
          {product.description && <p className="whitespace-pre-line">{product.description}</p>}
          {voice && (
            <div className="flex flex-col gap-2">
              <p className="text-small flex items-center gap-1 font-bold">
                <Waveform aria-hidden size={18} className="text-hibiscus" />
                {t("voice")}
              </p>
              <audio controls preload="none" src={voice} className="w-full">
                <track kind="captions" />
              </audio>
            </div>
          )}
        </section>
      )}

      {product.video?.status === "ready" && (
        <section aria-labelledby="video" className="flex flex-col gap-3">
          <h2 id="video" className="text-title font-bold">
            {t("video")}
          </h2>
          <VideoPlayer media={product.video} label={product.title} />
        </section>
      )}

      {product.delivery && (
        <section aria-labelledby="delivery" className="flex flex-col gap-3">
          <h2 id="delivery" className="text-title font-bold">
            {t("delivery")}
          </h2>
          <DeliveryInfo delivery={product.delivery} currency={product.currency} />
          <p className="bg-poudre rounded-2xl p-3">{t("protected")}</p>
        </section>
      )}

      <section aria-labelledby="reviews" className="flex flex-col gap-3">
        <h2 id="reviews" className="text-title flex items-center gap-2 font-bold">
          <Star aria-hidden size={24} weight="fill" className="text-or" />
          {reviews.count > 0 && reviews.average !== null
            ? t("reviews", {
                rating: reviews.average.toLocaleString(locale, { maximumFractionDigits: 1 }),
                count: reviews.count,
              })
            : t("noReviews")}
        </h2>
        <ul className="flex flex-col gap-3">
          {reviews.results.map((review) => (
            <li
              key={review.id}
              className="border-trait rounded-card flex flex-col gap-1 border p-4"
            >
              <p className="font-bold">
                {review.author}{" "}
                <span className="text-prune-doux font-normal">
                  {t("stars", { count: review.rating })}
                </span>
              </p>
              {review.text && <p>{review.text}</p>}
              {review.reply && (
                <p className="bg-poudre text-small rounded-2xl p-3">
                  {t("reply", { name: product.shop.name, text: review.reply })}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
