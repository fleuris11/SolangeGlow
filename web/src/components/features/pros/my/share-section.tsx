"use client";

import { Copy, FilePdf, ImageSquare, Printer, ShareNetwork } from "@phosphor-icons/react";
import { useTranslations } from "next-intl";

import { Button, buttonClasses } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { printableUrl, type MyPro } from "@/lib/api/pros";

import { SectionFrame } from "./section-frame";

/** Short link and QR code: card for social networks, A4 poster, sticker sheet. */
export function ShareSection({ pro }: { pro: MyPro }) {
  const t = useTranslations("pros.my.share");
  const toast = useToast();
  const link = pro.short_link;
  const shown = link.replace(/^https?:\/\//, "");

  const copy = async () => {
    await navigator.clipboard?.writeText(link);
    toast(t("copied"), "success");
  };

  const share = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: pro.business_name, url: link });
      } catch {
        // Closed by the pro: nothing to do.
      }
    } else await copy();
  };

  const downloads = [
    { name: "card.png" as const, icon: <ImageSquare aria-hidden size={24} weight="bold" /> },
    { name: "poster.pdf" as const, icon: <Printer aria-hidden size={24} weight="bold" /> },
    { name: "stickers.pdf" as const, icon: <FilePdf aria-hidden size={24} weight="bold" /> },
  ];

  return (
    <SectionFrame title={t("title")} help={t("help")}>
      <div className="bg-poudre rounded-card flex flex-col gap-3 p-5">
        <p className="text-small font-bold">{t("yourLink")}</p>
        <p className="font-display text-title font-black break-all">{shown}</p>
        <div className="grid grid-cols-2 gap-3">
          <Button variant="secondary" onClick={() => void copy()}>
            <Copy aria-hidden size={22} weight="bold" />
            {t("copy")}
          </Button>
          <Button onClick={() => void share()}>
            <ShareNetwork aria-hidden size={22} weight="bold" />
            {t("share")}
          </Button>
        </div>
      </div>

      {pro.slug && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element -- drawn by the backend */}
          <img
            src={printableUrl(pro.slug, "card.png")}
            alt={t("qrAlt", { link: shown })}
            width={1200}
            height={1500}
            loading="lazy"
            className="border-trait rounded-card mx-auto w-full max-w-xs border"
          />
          <ul className="flex flex-col gap-3">
            {downloads.map(({ name, icon }) => (
              <li key={name}>
                <a
                  href={printableUrl(pro.slug, name, true)}
                  download
                  className={buttonClasses({
                    variant: "secondary",
                    fullWidth: true,
                    className: "justify-start",
                  })}
                >
                  {icon}
                  <span className="flex flex-col text-left">
                    <span>{t(`downloads.${name.replace(".", "_") as "card_png"}`)}</span>
                    <span className="text-small text-prune-doux font-normal">
                      {t(`downloadsHint.${name.replace(".", "_") as "card_png"}`)}
                    </span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionFrame>
  );
}
