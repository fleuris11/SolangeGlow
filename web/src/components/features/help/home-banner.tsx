import { useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import type { Schemas } from "@/lib/api/client";
import { bannersOnServer } from "@/lib/api/server";
import { mediaSrc, videoSrc } from "@/lib/media";

type Banner = Schemas["Banner"];
export type BannerPlacement = Parameters<typeof bannersOnServer>[1];

/**
 * Copies a promo code when its button is touched, and says so on the button. Written into the
 * page (no JavaScript file, ADR-004): the announcements stay server components.
 */
const COPY_SCRIPT = `(function(){if(window.__sgCopy)return;window.__sgCopy=1;document.addEventListener("click",function(e){
var b=e.target&&e.target.closest&&e.target.closest("[data-sg-copy]");if(!b)return;var c=b.getAttribute("data-sg-copy");
var done=function(){var l=b.querySelector("[data-label]");if(!l)return;var o=l.textContent;l.textContent=b.getAttribute("data-done");
setTimeout(function(){l.textContent=o},2500)};
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(c).then(done,function(){})}
else{var t=document.createElement("textarea");t.value=c;document.body.appendChild(t);t.select();try{document.execCommand("copy");done()}catch(x){}t.remove()}})})()`;

/** The announcements written by the team (module 12): picture or video, text, code, button. */
export function HomeBanners({ banners }: { banners: Banner[] }) {
  const t = useTranslations("help.banner");
  if (banners.length === 0) return null;
  const withCode = banners.some((banner) => banner.promo_code);
  return (
    <>
      {banners.map((banner) => {
        const video = banner.video;
        const poster = video?.urls.poster_medium ?? video?.urls.poster_low ?? undefined;
        return (
          <aside
            key={banner.id}
            aria-label={t("aria")}
            className="border-trait rounded-card bg-carte flex flex-col gap-3 border p-4"
          >
            {video && videoSrc(video, true) ? (
              <video
                controls
                muted
                playsInline
                preload="none"
                poster={poster}
                aria-label={banner.title}
                className="rounded-photo bg-poudre aspect-[16/9] w-full object-cover"
              >
                <source src={videoSrc(video, true)} type="video/mp4" />
              </video>
            ) : (
              banner.image && (
                // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                <img
                  src={mediaSrc(banner.image, "medium", "large")}
                  alt=""
                  loading="lazy"
                  className="rounded-photo bg-poudre aspect-[16/7] w-full object-cover"
                />
              )
            )}
            <p className="text-lead font-bold">{banner.title}</p>
            {banner.text && <p>{banner.text}</p>}
            {banner.promo_code && (
              <p className="flex flex-wrap items-center gap-2">
                <span className="text-small text-prune-doux">{t("code")}</span>
                <span className="border-prune rounded-field border-2 border-dashed px-3 py-1 font-bold tracking-wider">
                  {banner.promo_code}
                </span>
                <button
                  type="button"
                  data-sg-copy={banner.promo_code}
                  data-done={t("copied")}
                  className={buttonClasses({ variant: "quiet", className: "min-h-12 px-3" })}
                >
                  <svg
                    aria-hidden
                    viewBox="0 0 256 256"
                    className="size-5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="18"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <rect x="40" y="88" width="128" height="128" rx="8" />
                    <path d="M88 88V40h128v128h-48" />
                  </svg>
                  <span data-label>{t("copy")}</span>
                </button>
              </p>
            )}
            {banner.link && (
              <a
                href={banner.link}
                className={buttonClasses({ variant: "secondary", className: "self-start" })}
              >
                {banner.cta || t("discover")}
              </a>
            )}
          </aside>
        );
      })}
      {withCode && <script dangerouslySetInnerHTML={{ __html: COPY_SCRIPT }} />}
    </>
  );
}

/** The announcements of one place of the app, fetched on the server (nothing when none). */
export async function Announcements({
  placement,
  locale,
}: {
  placement: BannerPlacement;
  locale: string;
}) {
  const banners = await bannersOnServer(locale, placement).catch(() => []);
  return <HomeBanners banners={banners} />;
}
