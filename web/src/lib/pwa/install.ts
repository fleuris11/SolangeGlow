/**
 * « Install the app » (PWA). The browser's offer is caught by an inline script of the
 * layout as soon as the page opens (no JavaScript file for it, ADR-004); the invitation
 * is shown only at the right moment: after a booking or an order, or from the 3rd visit.
 */
export const installCaptureScript = `(function(){
window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();window.__sgInstall=e;window.dispatchEvent(new Event("sg-installable"))});
try{if(!sessionStorage.getItem("sg.visit")){sessionStorage.setItem("sg.visit","1");localStorage.setItem("sg.visits",String(+(localStorage.getItem("sg.visits")||0)+1))}}catch(e){}
})();`;

export type InstallOffer = Event & { prompt: () => Promise<void>; userChoice: Promise<unknown> };

declare global {
  interface Window {
    __sgInstall?: InstallOffer;
  }
}

const DISMISSED = "sg.install-dismissed";

export function visits(): number {
  try {
    return Number(localStorage.getItem("sg.visits") ?? 0);
  } catch {
    return 0;
  }
}

/** « Later » keeps the invitation away for a while (days). */
export function dismissedRecently(days = 30): boolean {
  try {
    const at = Number(localStorage.getItem(DISMISSED) ?? 0);
    return Date.now() - at < days * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

export function dismiss(): void {
  try {
    localStorage.setItem(DISMISSED, String(Date.now()));
  } catch {
    // storage blocked: shown again next time
  }
}
