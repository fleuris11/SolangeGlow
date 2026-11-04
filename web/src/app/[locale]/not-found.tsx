import { useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import { Link } from "@/lib/i18n/navigation";

export default function NotFound() {
  const t = useTranslations("errors");
  return (
    <main id="main" className="mx-auto flex min-h-[70svh] max-w-[480px] flex-col justify-center gap-4 px-4">
      <h1 className="font-display text-display">{t("notFoundTitle")}</h1>
      <p className="text-lead">{t("notFoundText")}</p>
      <Link href="/" className={buttonClasses({ size: "lg" })}>
        {t("home")}
      </Link>
    </main>
  );
}
