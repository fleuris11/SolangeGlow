"use client";

import { useTranslations } from "next-intl";

const ACTION = "rounded-button inline-flex min-h-12 items-center justify-center px-5 font-semibold";

/** A page broke: clear words and a way out. Every page carries this file, so it stays tiny. */
export default function ErrorPage({ reset }: { reset: () => void }) {
  const t = useTranslations("errors");
  return (
    <main
      id="main"
      className="mx-auto flex min-h-[70svh] max-w-[480px] flex-col justify-center gap-4 px-4"
    >
      <h1 className="font-display text-display">{t("title")}</h1>
      <p className="text-lead">{t("text")}</p>
      <button type="button" onClick={reset} className={`${ACTION} bg-rouge text-sur-hibiscus`}>
        {t("retry")}
      </button>
      {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- a full reload is the point */}
      <a href="/" className={`${ACTION} border-prune border-2`}>
        {t("home")}
      </a>
    </main>
  );
}
