import { describe, expect, it } from "vitest";

import { applyOverrides } from "./overrides";

describe("applyOverrides", () => {
  const messages = { home: { question: "Tu cherches quoi ?", nested: { cta: "Voir" } }, top: "A" };

  it("replaces the texts found by their dotted key", () => {
    const merged = applyOverrides(messages, { "home.question": "Envie de quoi ?", top: "B" });
    expect(merged).toEqual({
      home: { question: "Envie de quoi ?", nested: { cta: "Voir" } },
      top: "B",
    });
    expect(messages.home.question).toBe("Tu cherches quoi ?");
  });

  it("ignores keys that do not exist or point to a group", () => {
    const merged = applyOverrides(messages, {
      "home.nope": "x",
      home: "x",
      "home.nested.cta.more": "x",
    });
    expect(merged).toEqual(messages);
  });
});
