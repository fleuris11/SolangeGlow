import { CalendarCheck, Clock, Heart, SealCheck } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Portrait } from "@/components/features/illustrations/portrait";
import { TradeLabel } from "@/components/features/trades/trade-label";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { PriceTag } from "@/components/ui/price-tag";
import { DEMO_LOOKS, DEMO_PROS } from "@/lib/demo/data";
import { Link } from "@/lib/i18n/navigation";

/** Before / after posts from pros, each with "Book this look". */
export function LooksFeed() {
  const t = useTranslations("home.looks");

  return (
    <section aria-labelledby="looks-title" className="flex flex-col gap-4">
      <div>
        <h2 id="looks-title" className="text-title font-bold">
          {t("title")}
        </h2>
        <p className="text-prune-doux">{t("subtitle")}</p>
      </div>

      <ul className="flex flex-col gap-6">
        {DEMO_LOOKS.map((look) => {
          const pro = DEMO_PROS.find((p) => p.id === look.proId);
          if (!pro) return null;
          const hours = Math.floor(look.durationMinutes / 60);
          const minutes = look.durationMinutes % 60;
          return (
            <li key={look.id}>
              <article
                aria-labelledby={`look-${look.id}`}
                className="border-trait bg-carte rounded-card overflow-hidden border"
              >
                <header className="flex items-center gap-3 p-4">
                  <Avatar name={pro.name} size="sm" picture={<Portrait {...pro.portrait} />} />
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-1 font-bold">
                      {pro.name}
                      {pro.verified && (
                        <SealCheck
                          size={18}
                          weight="fill"
                          className="text-feuille"
                          aria-label={t("verified")}
                        />
                      )}
                    </p>
                    <p className="text-small text-prune-doux truncate">
                      {pro.district}, {pro.city}
                    </p>
                  </div>
                  <TradeLabel trade={look.trade} className="text-small font-bold" />
                </header>

                <div className="grid grid-cols-2 gap-1 px-1">
                  <figure className="relative">
                    <div className="rounded-photo aspect-[4/5] overflow-hidden">
                      <Portrait skin={look.skin} look="natural" outfit="prune" />
                    </div>
                    <figcaption className="bg-carte text-small absolute top-2 left-2 rounded-full px-3 py-1 font-bold">
                      {t("before")}
                    </figcaption>
                  </figure>
                  <figure className="relative">
                    <div className="rounded-photo aspect-[4/5] overflow-hidden">
                      <Portrait
                        skin={look.skin}
                        look={look.after}
                        outfit={look.after === "headwrap" ? "hibiscus" : "or"}
                        accent={look.accent}
                      />
                    </div>
                    <figcaption className="bg-hibiscus text-sur-hibiscus text-small absolute top-2 left-2 rounded-full px-3 py-1 font-bold">
                      {t("after")}
                    </figcaption>
                  </figure>
                </div>

                <div className="flex flex-col gap-3 p-4">
                  <h3 id={`look-${look.id}`} className="text-lead font-bold">
                    {look.title}
                  </h3>
                  <p className="text-small text-prune-doux flex flex-wrap items-center gap-x-4 gap-y-1">
                    <span className="inline-flex items-center gap-1">
                      <Clock aria-hidden size={18} weight="duotone" />
                      {t("duration", { hours, minutes })}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Heart aria-hidden size={18} weight="duotone" />
                      {t("likes", { count: look.likes })}
                    </span>
                  </p>
                  <PriceTag amountMinor={look.amountMinor} currency={look.currency} size="lg" />
                  <Button asChild fullWidth size="lg">
                    <Link href="/auth?as=client">
                      <CalendarCheck aria-hidden size={22} weight="bold" />
                      {t("book")}
                    </Link>
                  </Button>
                </div>
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
