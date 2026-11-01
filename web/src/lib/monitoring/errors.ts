/**
 * Errors sent to GlitchTip with the Sentry protocol (prompt 19). No SDK on the phone: a
 * few lines inline, only when NEXT_PUBLIC_SENTRY_DSN is set. No personal data: the
 * address without its query and without long tokens, no cookie, no user.
 */
export const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN ?? "";
export const SENTRY_ENVIRONMENT = process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development";

/** The « store » address of a DSN (https://key@host/42), or null when it is not one. */
export function storeUrl(dsn: string): string | null {
  const match = /^(https?):\/\/([^@/]+)@([^/]+)\/(\d+)$/.exec(dsn.trim());
  if (!match) return null;
  const [, scheme, key, host, project] = match;
  return `${scheme}://${host}/api/${project}/store/?sentry_version=7&sentry_key=${key}`;
}

/** Long tokens (guest links, gifts) never leave the app in an error report. */
export function cleanPath(path: string): string {
  return path.replace(/[A-Za-z0-9_-]{20,}/g, "…");
}

export function errorEvent(
  error: { name?: string; message?: string; stack?: string },
  path: string,
  side: "browser" | "server",
) {
  return {
    platform: "javascript",
    level: "error",
    environment: SENTRY_ENVIRONMENT,
    timestamp: Date.now() / 1000,
    tags: { side },
    request: { url: cleanPath(path) },
    exception: {
      values: [{ type: error.name || "Error", value: String(error.message ?? "").slice(0, 500) }],
    },
    extra: { stack: String(error.stack ?? "").slice(0, 4000) },
  };
}

/** Inline in the layout: catches what breaks in the browser (5 reports per page at most). */
export function browserReporterScript(): string {
  const url = storeUrl(SENTRY_DSN);
  if (!url) return "";
  return `(function(){var u=${JSON.stringify(url)},E=${JSON.stringify(SENTRY_ENVIRONMENT)},n=0;
function send(t,v,s){if(++n>5)return;try{fetch(u,{method:"POST",keepalive:true,body:JSON.stringify({platform:"javascript",level:"error",environment:E,timestamp:Date.now()/1000,tags:{side:"browser"},request:{url:location.pathname.replace(/[A-Za-z0-9_-]{20,}/g,"…")},exception:{values:[{type:t||"Error",value:String(v||"").slice(0,500)}]},extra:{stack:String(s||"").slice(0,4000)}})})}catch(e){}}
window.__sgReport=function(e){send(e&&e.name,e&&e.message,e&&e.stack)};
addEventListener("error",function(e){send(e.error&&e.error.name,e.message,e.error&&e.error.stack)});
addEventListener("unhandledrejection",function(e){var r=e.reason||{};send(r.name,r.message||r,r.stack)});})();`;
}
