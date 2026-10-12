import { ChatCircleText, Star } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { Avatar } from "@/components/ui/avatar";
import type { ReviewPage } from "@/lib/api/social";
import { mediaSrc, voiceSrc } from "@/lib/media";

/** Verified reviews of a pro: average, how many of each star, the latest ones and her replies. */
export function ReviewsSection({ page, name }: { page: ReviewPage; name: string }) {
  const t = useTranslations("social.reviews");
  const locale = useLocale();
  const total = page.count || 1;

  return (
    <section aria-labelledby="reviews" className="flex flex-col gap-4">
      <h2 id="reviews" className="text-title flex items-center gap-2 font-bold">
        <Star aria-hidden size={26} weight="duotone" className="text-hibiscus" />
        {t("title")}
      </h2>
      <p className="text-small text-prune-doux">{t("verifiedOnly")}</p>
      {page.count === 0 ? (
        <p className="text-prune-doux">{t("none", { name })}</p>
      ) : (
        <>
          <div className="flex items-center gap-4">
            <p className="font-display text-display font-black">
              {(page.average ?? 0).toLocaleString(locale, { maximumFractionDigits: 1 })}
            </p>
            <div className="flex flex-1 flex-col gap-1">
              {[5, 4, 3, 2, 1].map((star) => {
                const count = page.distribution[String(star)] ?? 0;
                return (
                  <div key={star} className="text-small flex items-center gap-2">
                    <span className="w-14">{t("starsShort", { count: star })}</span>
                    <span className="bg-poudre h-2 flex-1 overflow-hidden rounded-full" aria-hidden>
                      <span
                        className="bg-or block h-full"
                        style={{ width: `${(count / total) * 100}%` }}
                      />
                    </span>
                    <span className="w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <p className="text-small">{t("count", { count: page.count })}</p>
          <ul className="flex flex-col gap-4">
            {page.results.map((review) => (
              <li key={review.id} className="border-trait flex flex-col gap-2 border-b pb-4">
                <div className="flex items-center gap-3">
                  <Avatar
                    name={review.author_name || "?"}
                    src={mediaSrc(review.author_photo, "thumb")}
                    size="sm"
                  />
                  <span className="flex flex-col">
                    <span className="font-bold">{review.author_name}</span>
                    <span className="text-mention text-prune-doux">
                      {t("starsValue", { count: review.rating })},{" "}
                      {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
                        new Date(review.created_at),
                      )}
                    </span>
                  </span>
                </div>
                <p className="flex gap-0.5" aria-hidden>
                  {[1, 2, 3, 4, 5].map((value) => (
                    <Star
                      key={value}
                      size={18}
                      weight={value <= review.rating ? "fill" : "regular"}
                      className={value <= review.rating ? "text-or" : "text-trait"}
                    />
                  ))}
                </p>
                {review.text && <p className="whitespace-pre-line">{review.text}</p>}
                {review.photo && (
                  // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                  <img
                    src={mediaSrc(review.photo, "medium", "thumb")}
                    alt={t("photoOf", { name: review.author_name })}
                    loading="lazy"
                    className="max-h-64 w-auto rounded-2xl object-cover"
                  />
                )}
                {voiceSrc(review.voice) && (
                  <audio controls preload="none" src={voiceSrc(review.voice)} className="w-full">
                    <track kind="captions" />
                  </audio>
                )}
                {review.reply && (
                  <div className="bg-poudre rounded-card flex gap-2 p-3">
                    <ChatCircleText aria-hidden size={20} className="text-hibiscus shrink-0" />
                    <p>
                      <span className="font-bold">{t("replyOf", { name })}</span> {review.reply}
                    </p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
