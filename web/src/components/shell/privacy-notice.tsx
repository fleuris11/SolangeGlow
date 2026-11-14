import { ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Link } from "@/lib/i18n/navigation";
import { consentScript, safePixelId } from "@/lib/consent/consent-script";

const PIXEL_ID = safePixelId(process.env.NEXT_PUBLIC_META_PIXEL_ID);

/**
 * Without the Meta pixel: what Solange Glow does with personal data, in two lines.
 * With it: the cookie consent banner (« Refuser » and « Accepter », same weight), shown before
 * anything from Meta loads. In the flow of the page (top): it never covers a button.
 * The logic is inline (lib/consent/consent-script.ts): no JavaScript file (ADR-004).
 */
export function PrivacyNotice() {
  const t = useTranslations("privacy");
  const consent = PIXEL_ID !== "";
  const button =
    "press border-prune text-small rounded-button min-h-11 border-2 px-4 font-semibold";
  return (
    <>
      <aside
        id="sg-privacy"
        aria-label={t("aria")}
        hidden
        suppressHydrationWarning
        className="bg-poudre flex flex-wrap items-center gap-3 px-4 py-3 [&[hidden]]:hidden"
      >
        <p className="text-small flex min-w-0 flex-1 basis-64 items-start gap-3">
          <ShieldCheck aria-hidden size={24} className="shrink-0" />
          <span>
            {consent ? t("consentText") : t("text")}{" "}
            <Link
              href="/pages/confidentialite"
              className="font-semibold underline underline-offset-4"
            >
              {t("more")}
            </Link>
          </span>
        </p>
        {consent ? (
          <span className="flex gap-2">
            <button type="button" data-consent="refuse" className={button}>
              {t("refuse")}
            </button>
            <button type="button" data-consent="accept" className={button}>
              {t("accept")}
            </button>
          </span>
        ) : (
          <button type="button" data-consent="accept" className={button}>
            {t("ok")}
          </button>
        )}
      </aside>
      <script dangerouslySetInnerHTML={{ __html: consentScript(PIXEL_ID) }} />
    </>
  );
}
