import { describe, expect, it } from "vitest";

import { cleanPath, errorEvent, storeUrl } from "./errors";

describe("error reports", () => {
  it("finds the store address of a DSN", () => {
    expect(storeUrl("https://abc123@errors.example.com/7")).toBe(
      "https://errors.example.com/api/7/store/?sentry_version=7&sentry_key=abc123",
    );
    expect(storeUrl("")).toBeNull();
    expect(storeUrl("not a dsn")).toBeNull();
  });

  it("never sends the token of a guest link", () => {
    expect(cleanPath("/fr/rdv/AbCdEfGhIjKlMnOpQrStUv")).toBe("/fr/rdv/…");
    const event = errorEvent(
      new TypeError("boom"),
      "/fr/cadeau/AbCdEfGhIjKlMnOpQrStUvWx",
      "server",
    );
    expect(event.request.url).toBe("/fr/cadeau/…");
    expect(event.exception.values[0]).toEqual({ type: "TypeError", value: "boom" });
  });
});
