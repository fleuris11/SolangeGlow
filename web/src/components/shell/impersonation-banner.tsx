import { SignOut, UserSwitch } from "@phosphor-icons/react/dist/ssr";
import { useTranslations } from "next-intl";

// Shows the banner when the cookie set by the back office exists (it holds no secret), and
// ends the session on « Stop ». Inline: no JavaScript file for everyone else (ADR-004).
const SCRIPT = `(function(){
var m=document.cookie.match(/(?:^|;\\s*)sg_impersonation=([^;]+)/);if(!m)return;
var b=document.getElementById("sg-imp"),t=b.querySelector("[data-named]"),n="";
try{n=decodeURIComponent(m[1].split("|")[1]||"")}catch(e){}
if(n)t.textContent=t.getAttribute("data-named").replace("%NAME%",n);
b.hidden=false;
var h={"X-SG-Client":"web"},o={method:"POST",headers:h,credentials:"same-origin"};
function stop(){return fetch("/api/v1/backoffice/impersonation/stop",o)}
b.querySelector("button").addEventListener("click",function(){
this.disabled=true;
stop().then(function(r){return r.status===401?fetch("/api/v1/auth/refresh",o).then(stop):r})
.catch(function(){}).then(function(){location.replace(location.origin)});
});
})()`;

/** Always on top while a team member uses the account of a member; everything is noted. */
export function ImpersonationBanner() {
  const t = useTranslations("impersonation");
  return (
    <>
      <div
        id="sg-imp"
        role="alert"
        hidden
        suppressHydrationWarning
        className="bg-hibiscus text-sur-hibiscus sticky top-0 z-50 flex flex-wrap items-center gap-3 px-4 py-2 [&[hidden]]:hidden"
      >
        <UserSwitch size={24} weight="duotone" aria-hidden />
        <p className="min-w-0 flex-1 font-bold">
          <span data-named={t("asNamed", { name: "%NAME%" })} suppressHydrationWarning>
            {t("asMember")}
          </span>
          <span className="text-small block font-normal">{t("traced")}</span>
        </p>
        <button
          type="button"
          className="border-sur-hibiscus inline-flex min-h-12 items-center gap-2 rounded-full border-2 px-5 font-bold disabled:opacity-50"
        >
          <SignOut size={20} aria-hidden />
          {t("stop")}
        </button>
      </div>
      <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />
    </>
  );
}
