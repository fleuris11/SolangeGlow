import { useTranslations } from "next-intl";
import Image from "next/image";

import { cn } from "@/lib/cn";

/** What the pro prints: a sample of the poster, with a QR code that really scans. */
export function QrPoster({ className }: { className?: string }) {
  const t = useTranslations("marketing.poster");
  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      {/* A sheet of paper: white in every theme, or the code would not scan. */}
      <div className="bg-sur-hibiscus text-rouge rounded-photo flex flex-col items-center gap-3 p-6 text-center">
        <p className="font-display text-title">{t("name")}</p>
        <Image
          src="/brand/qr-exemple.svg"
          alt={t("alt")}
          width={220}
          height={220}
          unoptimized
          className="size-44 lg:size-56"
        />
        <p className="font-semibold">{t("scan")}</p>
        <p className="text-small font-semibold">solangeglow.com/aicha</p>
      </div>
      <figcaption className="text-small text-prune-doux">{t("caption")}</figcaption>
    </figure>
  );
}
