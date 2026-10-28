import { Broadcast, Play } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import type { ShopPage } from "@/lib/api/shop";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

type ShopLive = ShopPage["lives"][number];

/** The lives of a shop: on air (first), coming, replays still visible. */
export function ShopLives({ lives }: { lives: ShopLive[] }) {
  const t = useTranslations("live.shop");
  const locale = useLocale();
  if (lives.length === 0) return null;
  const order = { live: 0, scheduled: 1, ended: 2, cancelled: 3 } as const;
  const sorted = [...lives].sort((a, b) => order[a.status] - order[b.status]);
  return (
    <section aria-labelledby="shop-lives" className="flex flex-col gap-3">
      <h2 id="shop-lives" className="text-title flex items-center gap-2 font-bold">
        <Broadcast aria-hidden size={26} weight="duotone" className="text-hibiscus" />
        {t("title")}
      </h2>
      <ul className="flex flex-col gap-2">
        {sorted.map((live) => (
          <li key={live.id}>
            <Link
              href={live.link}
              className={cn(
                "flex min-h-16 items-center gap-3 rounded-2xl border p-3",
                live.status === "live" ? "border-hibiscus bg-poudre border-2" : "border-trait",
              )}
            >
              {live.status === "ended" ? (
                <Play aria-hidden size={26} weight="fill" className="text-hibiscus shrink-0" />
              ) : (
                <Broadcast aria-hidden size={26} weight="bold" className="text-hibiscus shrink-0" />
              )}
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate font-bold">{live.title}</span>
                <span className="text-small text-prune-doux">
                  {live.status === "live"
                    ? t("onAir")
                    : live.status === "ended"
                      ? t("replay")
                      : new Intl.DateTimeFormat(locale, {
                          weekday: "long",
                          day: "numeric",
                          month: "long",
                          hour: "numeric",
                          minute: "2-digit",
                          timeZone: live.time_zone,
                        }).format(new Date(live.starts_at))}
                </span>
              </span>
              <span className="text-hibiscus shrink-0 font-bold">
                {live.status === "ended" ? t("watch") : t("open")}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
