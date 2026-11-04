import { ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

import { Link } from "@/lib/i18n/navigation";

// Shown once per browser (no cookie: the choice is kept in the storage of the page).
// Inline: no JavaScript file for this notice (ADR-004).
const SCRIPT = `(function(){try{if(localStorage.getItem("sg.privacy-notice"))return}catch(e){}
var b=document.getElementById("sg-privacy");b.hidden=false;
b.querySelector("button").addEventListener("click",function(){
try{localStorage.setItem("sg.privacy-notice","1")}catch(e){}b.hidden=true});})()`;

/** What Solange Glow does with personal data, in two lines, with a link to the policy.
 * In the flow of the page (top): it never covers a button. */
export function PrivacyNotice() {
  const t = useTranslations("privacy");
  return (
    <>
      <aside
        id="sg-privacy"
        aria-label={t("aria")}
        hidden
        suppressHydrationWarning
        className="bg-poudre border-trait flex flex-wrap items-center gap-3 border-b px-4 py-3 [&[hidden]]:hidden"
      >
        <p className="flex min-w-0 flex-1 basis-64 items-start gap-3">
          <ShieldCheck aria-hidden size={28} weight="duotone" className="text-feuille shrink-0" />
          <span>
            {t("text")}{" "}
            <Link href="/pages/confidentialite" className="text-hibiscus font-bold underline">
              {t("more")}
            </Link>
          </span>
        </p>
        <button
          type="button"
          className="bg-rouge text-sur-hibiscus min-h-12 rounded-full px-5 font-bold"
        >
          {t("ok")}
        </button>
      </aside>
      <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />
    </>
  );
}
