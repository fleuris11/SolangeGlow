import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CONSENT_KEY,
  CONSENT_MAX_AGE_MS,
  LEGACY_NOTICE_KEY,
  consentScript,
  safePixelId,
} from "./consent-script";

type Win = Window & { fbq?: unknown; sgConsent?: { open: () => void; ads: () => boolean } };

function mount(pixel: string) {
  document.body.innerHTML = `<script></script><aside id="sg-privacy" hidden>
    <button data-consent="refuse"></button><button data-consent="accept"></button></aside>
    <button data-consent-open id="open"></button>`;
  // Same as the inline <script> of the layout.
  new Function(consentScript(pixel))();
  return document.getElementById("sg-privacy") as HTMLElement;
}

const click = (selector: string) => (document.querySelector(selector) as HTMLElement).click();

describe("cookie consent", () => {
  beforeEach(() => {
    localStorage.clear();
    delete (window as Win).fbq;
    delete (window as Win).sgConsent;
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    document.head.querySelectorAll("script[src]").forEach((s) => s.remove());
    document.querySelectorAll("script[src]").forEach((s) => s.remove());
  });

  it("only accepts a numeric pixel id", () => {
    expect(safePixelId("1234567890")).toBe("1234567890");
    expect(safePixelId('1";alert(1)//')).toBe("");
    expect(safePixelId(undefined)).toBe("");
  });

  it("without a pixel: the simple notice, nothing from Meta", () => {
    const banner = mount("");
    expect(banner.hidden).toBe(false);
    click("[data-consent=accept]");
    expect(banner.hidden).toBe(true);
    expect(localStorage.getItem(LEGACY_NOTICE_KEY)).toBe("1");
    expect((window as Win).fbq).toBeUndefined();
  });

  it("with a pixel: nothing loads before a choice", () => {
    const banner = mount("1234567890");
    expect(banner.hidden).toBe(false);
    expect((window as Win).fbq).toBeUndefined();
    expect(document.querySelector('script[src*="facebook"]')).toBeNull();
  });

  it("« Refuser » keeps Meta out and remembers the choice", () => {
    const banner = mount("1234567890");
    click("[data-consent=refuse]");
    expect(banner.hidden).toBe(true);
    expect(JSON.parse(localStorage.getItem(CONSENT_KEY)!).ads).toBe(false);
    expect((window as Win).fbq).toBeUndefined();
    expect((window as Win).sgConsent!.ads()).toBe(false);
  });

  it("« Accepter » loads the pixel, and on the next visit without asking", () => {
    mount("1234567890");
    click("[data-consent=accept]");
    expect(typeof (window as Win).fbq).toBe("function");
    expect(document.querySelector('script[src*="connect.facebook.net"]')).not.toBeNull();

    delete (window as Win).fbq;
    const banner = mount("1234567890");
    expect(banner.hidden).toBe(true);
    expect(typeof (window as Win).fbq).toBe("function");
  });

  it("asks again after 6 months", () => {
    localStorage.setItem(
      CONSENT_KEY,
      JSON.stringify({ ads: true, at: Date.now() - CONSENT_MAX_AGE_MS - 1000, v: 1 }),
    );
    const banner = mount("1234567890");
    expect(banner.hidden).toBe(false);
    expect((window as Win).fbq).toBeUndefined();
  });

  it("the footer link opens the banner again", () => {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ ads: false, at: Date.now(), v: 1 }));
    const banner = mount("1234567890");
    expect(banner.hidden).toBe(true);
    click("#open");
    expect(banner.hidden).toBe(false);
  });
});
