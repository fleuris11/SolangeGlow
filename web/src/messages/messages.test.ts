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
});
