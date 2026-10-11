"use client";

import { ArrowLeft } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { SpeakButton } from "@/components/ui/speak-button";
import { Link } from "@/lib/i18n/navigation";

/** One part of « Ma vitrine »: a way back, a title (read aloud), a short help. */
export function SectionFrame({
  title,
  help,
  children,
}: {
  title: string;
  help: string;
  children: ReactNode;
}) {
  const t = useTranslations("pros.my");
  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/pro"
        className="text-hibiscus -ml-1 inline-flex min-h-12 items-center gap-2 self-start font-bold"
      >
        <ArrowLeft aria-hidden size={22} weight="bold" />
        {t("back")}
      </Link>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-headline font-bold">{title}</h1>
          <p className="text-prune-doux">{help}</p>
        </div>
        <SpeakButton text={`${title}. ${help}`} />
      </div>
      {children}
    </div>
  );
}

export const fieldClass =
  "rounded-field bg-poudre focus:border-hibiscus min-h-14 w-full border-2 border-transparent px-4 py-3 outline-none";
