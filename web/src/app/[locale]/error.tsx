"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { Button, buttonClasses } from "@/components/ui/button";
import { Link } from "@/lib/i18n/navigation";

/** Something broke on a page: clear words and a way out, never a technical message. */
export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  const t = useTranslations("errors");
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main id="main" className="mx-auto flex min-h-[70svh] max-w-[480px] flex-col justify-center gap-4 px-4">
      <h1 className="font-display text-display">{t("title")}</h1>
      <p className="text-lead">{t("text")}</p>
      <Button size="lg" onClick={reset}>
        {t("retry")}
      </Button>
      <Link href="/" className={buttonClasses({ variant: "secondary" })}>
        {t("home")}
      </Link>
    </main>
  );
}
