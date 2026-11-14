/**
 * Cookie consent and Meta pixel (CNIL rules).
 *
 * - No pixel id set: the banner is the old privacy notice (no tracker, nothing to accept).
 * - Pixel id set: nothing from Meta loads before a « yes ». « Refuser » is as easy as
 *   « Accepter », the choice is asked again after 6 months, and the footer link
 *   « Gérer mes cookies » (window.sgConsent.open()) lets the person change her mind.
 *
 * Inline: no JavaScript file for the banner (ADR-004 budget). Kept as a string built here so
 * it can be tested in jsdom (consent.test.ts).
 */

export const CONSENT_KEY = "sg.consent";
export const LEGACY_NOTICE_KEY = "sg.privacy-notice";
/** 6 months, the period the CNIL recommends before asking again. */
export const CONSENT_MAX_AGE_MS = 182 * 24 * 60 * 60 * 1000;

/** Only digits: a Meta pixel id. Anything else turns the pixel off. */
export function safePixelId(raw: string | undefined): string {
  return raw && /^\d{6,20}$/.test(raw) ? raw : "";
}

export function consentScript(pixelId: string): string {
  const id = safePixelId(pixelId);
  return `(function(){
var PIXEL=${JSON.stringify(id)},KEY=${JSON.stringify(CONSENT_KEY)},LEGACY=${JSON.stringify(LEGACY_NOTICE_KEY)},MAX=${CONSENT_MAX_AGE_MS};
var b=document.getElementById("sg-privacy");if(!b)return;
function read(){try{var v=JSON.parse(localStorage.getItem(KEY)||"null");
if(v&&typeof v.ads==="boolean"&&Date.now()-v.at<MAX)return v}catch(e){}return null}
function save(ads){try{localStorage.setItem(KEY,JSON.stringify({ads:ads,at:Date.now(),v:1}))}catch(e){}}
function loadPixel(){if(!PIXEL||window.fbq)return;
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version="2.0";n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;
s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,"script","https://connect.facebook.net/en_US/fbevents.js");
window.fbq("init",PIXEL);window.fbq("track","PageView")}
function show(){b.hidden=false}
function hide(){b.hidden=true}
function choose(ads){save(ads);hide();if(ads)loadPixel();
try{document.dispatchEvent(new CustomEvent("sg:consent",{detail:{ads:ads}}))}catch(e){}
if(!ads&&window.fbq){location.reload()}}
window.sgConsent={open:show,ads:function(){var c=read();return !!(c&&c.ads)}};
document.addEventListener("click",function(e){var t=e.target;if(t&&t.closest&&t.closest("[data-consent-open]")){show();try{b.scrollIntoView({block:"start"})}catch(e){}}});
var accept=b.querySelector("[data-consent=accept]"),refuse=b.querySelector("[data-consent=refuse]");
if(!PIXEL){
try{if(localStorage.getItem(LEGACY))return}catch(e){}
show();if(accept)accept.addEventListener("click",function(){try{localStorage.setItem(LEGACY,"1")}catch(e){}hide()});return}
if(accept)accept.addEventListener("click",function(){choose(true)});
if(refuse)refuse.addEventListener("click",function(){choose(false)});
var c=read();if(!c){show();return}if(c.ads)loadPixel();
})()`;
}
