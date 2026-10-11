"use client";

import { WhatsappLogo } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { buttonClasses } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";

function whatsappUrl(number: string, text: string) {
  return `https://wa.me/${number.replace(/[^\d]/g, "")}?text=${encodeURIComponent(text)}`;
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  whatsapp?: string;
};

/** Online booking comes with module 8; until then, write to the pro on WhatsApp. */
export function BookSheet({ open, onOpenChange, name, whatsapp }: Props) {
  const t = useTranslations("pros.showcase");
  return (
    <Sheet
      open={open}
      onOpenChange={onOpenChange}
      title={t("bookSoonTitle")}
      description={t("bookSoonText", { name })}
    >
      {whatsapp ? (
        <a
          href={whatsappUrl(whatsapp, t("whatsappText", { name }))}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonClasses({ size: "lg", fullWidth: true })}
        >
          <WhatsappLogo aria-hidden size={26} weight="bold" />
          {t("whatsapp")}
        </a>
      ) : (
        <p className="text-prune-doux">{t("bookSoonVisit")}</p>
      )}
    </Sheet>
  );
}
