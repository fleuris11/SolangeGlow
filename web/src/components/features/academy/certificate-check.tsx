import { SealCheck, SealWarning } from "@phosphor-icons/react/dist/ssr";
import { useLocale, useTranslations } from "next-intl";

import { SpeakButton } from "@/components/ui/speak-button";
import type { Schemas } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { Link } from "@/lib/i18n/navigation";

/** The public page opened by the QR code of a certificate: valid or not, for whom, what. */
export function CertificateCheckView({
  code,
  certificate,
}: {
  code: string;
  certificate: Schemas["CertificateCheck"] | null;
}) {
  const t = useTranslations("academy.certificate");
  const locale = useLocale();
  const date = (value: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(new Date(value));

  if (!certificate) {
    return (
      <article className="flex flex-col items-center gap-4 text-center">
        <SealWarning aria-hidden size={64} weight="duotone" className="text-alerte" />
        <h1 className="text-headline font-bold">{t("unknown")}</h1>
        <p>{t("unknownHelp", { code })}</p>
      </article>
    );
  }
  const valid = certificate.valid;
  const summary = valid
    ? t("valid", {
        name: certificate.holder_name,
        course: certificate.course_title,
        date: date(certificate.issued_at),
      })
    : t("revoked");

  return (
    <article className="flex flex-col items-center gap-5 text-center">
      {valid ? (
        <SealCheck aria-hidden size={72} weight="duotone" className="text-feuille" />
      ) : (
        <SealWarning aria-hidden size={72} weight="duotone" className="text-alerte" />
      )}
      <div className="flex items-start gap-2">
        <h1 className={cn("text-headline font-bold", valid ? "text-feuille" : "text-alerte")}>
          {valid ? t("validTitle") : t("revokedTitle")}
        </h1>
        <SpeakButton text={summary} />
      </div>
      <dl className="border-trait bg-carte rounded-card grid w-full max-w-md gap-3 border p-5 text-left">
        <Row label={t("holder")} value={certificate.holder_name} />
        <Row label={t("course")} value={certificate.course_title} />
        <Row label={t("trainer")} value={certificate.trainer_name} />
        <Row label={t("issued")} value={date(certificate.issued_at)} />
        <Row label={t("code")} value={certificate.code} />
      </dl>
      {!valid && <p>{summary}</p>}
      {certificate.course_slug && (
        <Link href={`/academie/${certificate.course_slug}`} className="font-bold underline">
          {t("seeCourse")}
        </Link>
      )}
    </article>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-small text-prune-doux">{label}</dt>
      <dd className="font-bold break-words">{value}</dd>
    </div>
  );
}
