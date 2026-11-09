/**
 * The country whose content the person sees (feed, search, lives, courses): found from her time
 * zone on her first visit, changed by her in the city picker. Kept in a cookie so the pages drawn
 * by the server show the same country; sent to the API as X-SG-Country (apps/core/viewer.py).
 * "*" means every country.
 */
export const COUNTRY_COOKIE = "sg_country";
export const EVERYWHERE = "*";
export const COUNTRY_EVENT = "sg:country";

export function readViewerCountry(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)sg_country=([^;]*)/);
  return match ? decodeURIComponent(match[1] ?? "") : "";
}

export function writeViewerCountry(code: string) {
  const value = code === EVERYWHERE ? EVERYWHERE : code.toUpperCase().slice(0, 2);
  document.cookie = `${COUNTRY_COOKIE}=${encodeURIComponent(value)}; Path=/; Max-Age=31536000; SameSite=Lax`;
  window.dispatchEvent(new Event(COUNTRY_EVENT));
}

/**
 * First visit only: the country is found from the time zone of the device (no permission asked).
 * A generic zone (UTC, GMT, Etc/…) names no country: every country is shown.
 * Written into the page, no JavaScript file (ADR-004); waits until the page is shown. The pages
 * opened next follow that country; she can change it in the city picker.
 */
export const countryDetectScript = `(function(){try{if(/(?:^|;\\s*)sg_country=/.test(document.cookie))return;
setTimeout(function(){var z=Intl.DateTimeFormat().resolvedOptions().timeZone;
fetch("/api/v1/countries",{headers:{"X-SG-Client":"web"}}).then(function(r){return r.ok?r.json():[]}).then(function(l){
var c="*";if(z&&!/^(UTC|GMT|Etc\\/)/.test(z))for(var i=0;i<l.length;i++)if(l[i].timezone===z){c=l[i].code;break}
document.cookie="sg_country="+encodeURIComponent(c)+"; Path=/; Max-Age=31536000; SameSite=Lax";
window.dispatchEvent(new Event("sg:country"))}).catch(function(){})},1500)}catch(e){}})()`;
