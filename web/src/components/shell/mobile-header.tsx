import { MagnifyingGlass } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Link } from "@/lib/i18n/navigation";

import { AudioToggle } from "./audio-toggle";
import { CityPicker } from "./city-picker";

/** Mobile header: chosen city, search, audio mode. */
export function MobileHeader() {
  const t = useTranslations("header");
  return (
    <header className="bg-lait border-trait sticky top-0 z-30 border-b lg:hidden">
      <div className="mx-auto flex max-w-[640px] items-center gap-1 px-2 py-1">
        <CityPicker className="min-w-0 flex-1 justify-start" />
        <Link
          href="/explore"
          className="text-mention hover:bg-poudre inline-flex min-h-12 min-w-14 shrink-0 flex-col items-center justify-center rounded-2xl px-2 font-bold"
        >
          <MagnifyingGlass aria-hidden size={24} weight="bold" />
          <span>{t("search")}</span>
        </Link>
        <AudioToggle compact />
      </div>
    </header>
  );
}
