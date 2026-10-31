import { describe, expect, it } from "vitest";

import { routing } from "@/lib/i18n/routing";

import en from "./en.json";
import fr from "./fr.json";
import sk from "./sk.json";

const catalogs: Record<string, unknown> = { fr, en, sk };

function keys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
}

describe("translations", () => {
  it("has a catalog for every locale", () => {
    expect(Object.keys(catalogs).sort()).toEqual([...routing.locales].sort());
  });

  it.each(["en", "sk"])("%s has exactly the same keys as fr", (locale) => {
    expect(keys(catalogs[locale]).sort()).toEqual(keys(fr).sort());
  });

  it.each(Object.keys(catalogs))("%s has no empty text", (locale) => {
    const empty = keys(catalogs[locale]).filter((key) => {
      const value = key
        .split(".")
        .reduce<unknown>((node, part) => (node as Record<string, unknown>)[part], catalogs[locale]);
      return typeof value !== "string" || value.trim() === "";
    });
    expect(empty).toEqual([]);
  });

  it("sk is translated, not left in English", () => {
    // Same in both languages on purpose: names, units, placeholders.
    const same = new Set([
      "audio.stopShort",
      "messages.thread.online",
      "auth.phone.countries.BJ",
      "pros.languages.guw",
      "social.post.beforeAfterAlt",
      "shop.product.video",
      "shop.checkout.spokenOrder",
      "shop.detail.reference",
      "academy.mine.size",
      "academy.studio.countries.BJ",
      "calls.video",
    ]);
    const text = (catalog: unknown, key: string) =>
      key
        .split(".")
        .reduce<unknown>((node, part) => (node as Record<string, unknown>)[part], catalog);
    const english = keys(en).filter(
      (key) => !same.has(key) && text(sk, key) === text(en, key) && text(en, key) !== text(fr, key),
    );
    expect(english).toEqual([]);
  });
});
