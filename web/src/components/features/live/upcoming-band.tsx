import { Broadcast, GraduationCap, ShoppingBag } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import type { UpcomingLive } from "@/lib/api/live";
import { Link } from "@/lib/i18n/navigation";
import { mediaSrc } from "@/lib/media";

function when(live: UpcomingLive, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: live.time_zone,
  }).format(new Date(live.starts_at));
}

/** « Coming lives » on the home page: trainings and sales, the ones on air first. */
export function UpcomingLivesBand({ lives }: { lives: UpcomingLive[] }) {
  const t = useTranslations("live.home");
  const locale = useLocale();
  if (lives.length === 0) return null;
  return (
    <section aria-labelledby="lives-title" className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <Broadcast aria-hidden size={30} weight="duotone" className="text-hibiscus shrink-0" />
        <h2 id="lives-title" className="text-title font-bold">
          {t("title")}
        </h2>
      </div>
      <ul className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-2">
        {lives.map((live) => {
          const Icon = live.kind === "sale" ? ShoppingBag : GraduationCap;
          const href =
            live.on_air || live.kind === "sale"
              ? `/live/${live.kind}/${live.source_id}`
              : live.link;
          const photo = mediaSrc(live.host.photo, "thumb");
          return (
            <li key={`${live.kind}-${live.source_id}`} className="w-64 shrink-0">
              <Link
                href={href}
                className="border-trait bg-carte rounded-card flex h-full flex-col gap-2 border p-4"
              >
                <span className="flex items-center gap-2">
                  {live.on_air ? (
                    <span className="bg-hibiscus text-sur-hibiscus text-mention inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-bold">
                      <Broadcast aria-hidden size={16} weight="bold" />
                      {t("onAir")}
                    </span>
                  ) : (
                    <span className="text-small text-prune-doux font-bold">
                      {when(live, locale)}
                    </span>
                  )}
                  <span className="text-mention text-prune-doux ml-auto inline-flex items-center gap-1 font-bold">
                    <Icon aria-hidden size={16} weight="bold" />
                    {t(live.kind)}
                  </span>
                </span>
                <span className="line-clamp-2 font-bold">{live.title}</span>
                <span className="text-small text-prune-doux mt-auto flex items-center gap-2">
                  {photo ? (
                    // eslint-disable-next-line @next/next/no-img-element -- resized by the backend
                    <img
                      src={photo}
                      alt=""
                      loading="lazy"
                      width={28}
                      height={28}
                      className="petal size-7 shrink-0 object-cover"
                    />
                  ) : null}
                  <span className="truncate">{live.host.name}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
