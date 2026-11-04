"use client";

import { Broadcast, GraduationCap } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";

import { buttonClasses } from "@/components/ui/button";
import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";

const MySaleLivesTab = dynamic(() =>
  import("@/components/features/live/my-sale-lives").then((m) => m.MySaleLivesTab),
);

/** Going live, from one place: to sell from her shop, or to teach. */
export function LivesScreen() {
  const t = useTranslations("proSpace.lives");
  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-display">{t("title")}</h1>
          <p className="text-prune-doux">{t("line")}</p>
        </div>
        <SpeakButton text={t("title")} />
      </header>
      <section
        aria-labelledby="sale-lives"
        className="border-trait rounded-card flex flex-col gap-4 border p-4"
      >
        <h2 id="sale-lives" className="text-title flex items-center gap-2 font-bold">
          <Broadcast aria-hidden size={24} />
          {t("saleTitle")}
        </h2>
        <MySaleLivesTab />
      </section>
      <section
        aria-labelledby="course-lives"
        className="border-trait rounded-card flex flex-col items-start gap-3 border p-4"
      >
        <h2 id="course-lives" className="text-title flex items-center gap-2 font-bold">
          <GraduationCap aria-hidden size={24} />
          {t("courseTitle")}
        </h2>
        <p className="text-prune-doux">{t("courseText")}</p>
        <Link href="/pro/academy" className={buttonClasses({ variant: "secondary" })}>
          {t("courseCta")}
        </Link>
      </section>
    </div>
  );
}
