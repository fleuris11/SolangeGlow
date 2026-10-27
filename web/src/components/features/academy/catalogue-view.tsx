import {
  BookOpenText,
  Broadcast,
  Funnel,
  GraduationCap,
  MagnifyingGlass,
  Ticket,
} from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { SpeakButton } from "@/components/ui/speak-button";
import type { Schemas } from "@/lib/api/client";
import { Link } from "@/lib/i18n/navigation";
import { formatMoney } from "@/lib/money";

import { CourseCard } from "./course-card";

export type CatalogueFilters = {
  q?: string;
  trade?: string;
  level?: string;
  language?: string;
  pricing?: string;
};

const selectClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-3 text-body font-bold outline-none";

/** The academy: short video courses, filters that work without script, the pass. */
export function CatalogueView({
  page,
  trades,
  filters,
}: {
  page: Schemas["Catalogue"];
  trades: Schemas["Trade"][];
  filters: CatalogueFilters;
}) {
  const t = useTranslations("academy.catalogue");
  const tLevels = useTranslations("academy.levels");
  const tPricing = useTranslations("academy.pricing");
  const tLanguages = useTranslations("academy.languages");
  const locale = useLocale();
  const offer = page.pass_offer;
  const params = new URLSearchParams(
    Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1])),
  );

  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-start gap-2">
          <h1 className="font-display text-display flex-1 font-black">{t("title")}</h1>
          <SpeakButton text={`${t("title")}. ${t("intro")}`} />
        </div>
        <p className="text-lead">{t("intro")}</p>
        <nav aria-label={t("spaces")} className="flex flex-wrap gap-2">
          <Link href="/academie/mes-formations" className={buttonClasses({ variant: "secondary" })}>
            <BookOpenText aria-hidden size={22} weight="duotone" />
            {t("mine")}
          </Link>
          <Link href="/academie/lives" className={buttonClasses({ variant: "secondary" })}>
            <Broadcast aria-hidden size={22} weight="duotone" />
            {t("lives")}
          </Link>
        </nav>
      </header>

      {offer.price_minor !== null && offer.price_minor !== undefined && (
        <Link
          href="/academie/pass"
          className="bg-poudre rounded-card flex min-h-16 items-center gap-4 p-4"
        >
          <Ticket aria-hidden size={36} weight="duotone" className="text-hibiscus shrink-0" />
          <span className="flex flex-1 flex-col">
            <span className="font-bold">{offer.active ? t("passActive") : t("passTitle")}</span>
            <span className="text-small text-prune-doux">
              {t("passPrice", { price: formatMoney(offer.price_minor, offer.currency, locale) })}
            </span>
          </span>
        </Link>
      )}

      <form method="get" className="flex flex-col gap-3" role="search">
        <label htmlFor="academy-q" className="font-bold">
          {t("search")}
        </label>
        <div className="rounded-field bg-poudre focus-within:border-hibiscus flex min-h-14 items-center gap-2 border-2 border-transparent px-4">
          <MagnifyingGlass aria-hidden size={22} className="text-prune-doux" />
          <input
            id="academy-q"
            name="q"
            defaultValue={filters.q ?? ""}
            placeholder={t("searchPlaceholder")}
            className="text-body placeholder:text-prune-doux min-w-0 flex-1 bg-transparent py-3 outline-none"
          />
        </div>
        <details className="flex flex-col gap-3" open={Boolean(params.size && !filters.q)}>
          <summary className="flex min-h-12 cursor-pointer items-center gap-2 font-bold">
            <Funnel aria-hidden size={22} />
            {t("filters")}
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Choice id="academy-trade" name="trade" label={t("trade")} value={filters.trade}>
              <option value="">{t("all")}</option>
              {trades.map((trade) => (
                <option key={trade.key} value={trade.key}>
                  {trade.name}
                </option>
              ))}
            </Choice>
            <Choice id="academy-level" name="level" label={t("level")} value={filters.level}>
              <option value="">{t("all")}</option>
              {(["beginner", "intermediate", "expert"] as const).map((level) => (
                <option key={level} value={level}>
                  {tLevels(level)}
                </option>
              ))}
            </Choice>
            <Choice
              id="academy-language"
              name="language"
              label={t("language")}
              value={filters.language}
            >
              <option value="">{t("all")}</option>
              {(["fr", "en", "sk"] as const).map((language) => (
                <option key={language} value={language}>
                  {tLanguages(language)}
                </option>
              ))}
            </Choice>
            <Choice id="academy-pricing" name="pricing" label={t("price")} value={filters.pricing}>
              <option value="">{t("all")}</option>
              {(["free", "paid", "pass"] as const).map((pricing) => (
                <option key={pricing} value={pricing}>
                  {tPricing(pricing)}
                </option>
              ))}
            </Choice>
          </div>
        </details>
        <button type="submit" className={buttonClasses({ fullWidth: true })}>
          <MagnifyingGlass aria-hidden size={22} weight="bold" />
          {t("show")}
        </button>
      </form>

      {!page.open ? (
        <EmptyState
          icon={<GraduationCap size={44} weight="duotone" />}
          title={t("closed")}
          description={t("closedHelp")}
        />
      ) : page.results.length === 0 ? (
        <EmptyState
          icon={<GraduationCap size={44} weight="duotone" />}
          title={t("empty")}
          description={t("emptyHelp")}
          action={
            params.size ? (
              <Link href="/academie" className={buttonClasses({ variant: "secondary" })}>
                {t("clear")}
              </Link>
            ) : undefined
          }
        />
      ) : (
        <section aria-labelledby="academy-results" className="flex flex-col gap-4">
          <h2 id="academy-results" className="text-title font-bold">
            {t("results")}
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {page.results.map((course) => (
              <li key={course.id}>
                <CourseCard course={course} />
              </li>
            ))}
          </ul>
          {page.next && (
            <Link
              href={`/academie?${new URLSearchParams({ ...Object.fromEntries(params), cursor: page.next })}`}
              className={buttonClasses({ variant: "secondary", fullWidth: true })}
            >
              {t("more")}
            </Link>
          )}
        </section>
      )}
    </article>
  );
}

function Choice({
  id,
  name,
  label,
  value,
  children,
}: {
  id: string;
  name: string;
  label: string;
  value?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-small text-prune-doux font-bold">
        {label}
      </label>
      <select id={id} name={name} defaultValue={value ?? ""} className={selectClass}>
        {children}
      </select>
    </div>
  );
}
