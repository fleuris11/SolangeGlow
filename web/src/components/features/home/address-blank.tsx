import { useLocale, useTranslations } from "next-intl";

import { TITLE } from "@/components/features/marketing/chrome";
import { EditorialSection } from "@/components/ui/editorial-section";

/** The closing sentence has a gap: the name of the visitor, in the address of their own page. */
export function AddressBlank() {
  const t = useTranslations("landing.address");
  const locale = useLocale();
  return (
    <EditorialSection
      ambiance="nuit"
      aria-labelledby="address-title"
      className="px-4 py-16 md:px-8 xl:px-10 xl:py-24"
    >
      <h2
        id="address-title"
        className={`${TITLE} text-[clamp(2.25rem,10vw,3rem)] leading-none xl:text-[clamp(4rem,6vw,7rem)]`}
      >
        {t("title")}
      </h2>
      <form
        action={`/${locale}/auth`}
        method="get"
        className="font-display mt-2 flex flex-wrap items-center gap-x-[0.2em] gap-y-2 text-[clamp(1.875rem,8.4vw,3rem)] leading-none xl:text-[clamp(4rem,6vw,7rem)]"
      >
        <input type="hidden" name="as" value="pro" />
        <span className="max-sm:basis-full">solangeglow.com/</span>
        <label htmlFor="address-name" className="sr-only">
          {t("label")}
        </label>
        <input
          id="address-name"
          name="vitrine"
          required
          maxLength={60}
          autoComplete="organization"
          placeholder={t("placeholder")}
          className="bg-poudre placeholder:text-prune-doux rounded-button min-w-0 flex-1 px-[0.25em] pt-[0.22em] pb-[0.1em] tracking-[-0.03em] outline-offset-2 xl:max-w-[7em]"
        />
        <button
          type="submit"
          className="press bg-rouge text-sur-hibiscus hover:bg-rouge-press rounded-button cursor-pointer px-[0.35em] pt-[0.22em] pb-[0.1em] tracking-[-0.03em]"
        >
          {t("cta")}
        </button>
      </form>
      <p className="mt-5">{t("line")}</p>
    </EditorialSection>
  );
}
