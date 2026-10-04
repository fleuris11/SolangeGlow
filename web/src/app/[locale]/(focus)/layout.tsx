import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import { hasLocale, useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use, type ReactNode } from "react";

import { Link } from "@/lib/i18n/navigation";
import { routing } from "@/lib/i18n/routing";

type Props = { children: ReactNode; params: Promise<{ locale: string }> };

/** Focused screens (sign-in, welcome): no menu, one main action. */
export default function FocusLayout({ children, params }: Props) {
  const { locale } = use(params);
  setRequestLocale(hasLocale(routing.locales, locale) ? locale : routing.defaultLocale);
  const t = useTranslations("common");
  const tMeta = useTranslations("metadata");

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col px-4 pb-10">
      <header className="flex items-center justify-between py-3">
        <Link
          href="/"
          aria-label={t("backHome")}
          className="hover:bg-poudre -ml-2 inline-flex size-12 items-center justify-center rounded-full"
        >
          <ArrowLeft aria-hidden size={26} weight="bold" />
        </Link>
        <Image src="/icons/logo.png" alt={tMeta("title")} width={96} height={47} priority />
        <span aria-hidden className="size-12" />
      </header>
      <main id="main" className="flex-1 pt-2">
        {children}
      </main>
    </div>
  );
}
