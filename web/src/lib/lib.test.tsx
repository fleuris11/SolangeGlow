import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DisplaySettings } from "@/components/features/settings/display-settings";
import { renderWithProviders } from "@/test/render";

import { formatMoney } from "./money";
import { DEFAULT_PREFERENCES, parsePreferences, STORAGE_KEY } from "./preferences/preferences";
import { formatTimeOfDay } from "./time";

describe("formatMoney", () => {
  it.each([
    [15000, "XOF", "fr", "15 000 FCFA"],
    [15000, "XOF", "en", "15,000 FCFA"],
    [2500, "EUR", "fr", "25,00 €"],
    [2500, "EUR", "en", "€25.00"],
    [123456, "EUR", "sk", "1 234,56 €"],
  ])("%i %s in %s", (amount, currency, locale, expected) => {
    expect(formatMoney(amount, currency, locale)).toBe(expected);
  });

  it("refuses non-integer amounts and unknown currencies", () => {
    expect(() => formatMoney(10.5, "XOF", "fr")).toThrow();
    expect(() => formatMoney(100, "ABC", "fr")).toThrow();
  });
});

describe("formatTimeOfDay", () => {
  it("says times the French way", () => {
    expect(formatTimeOfDay(14, 0, "fr")).toBe("14 h");
    expect(formatTimeOfDay(9, 30, "fr")).toBe("9 h 30");
  });

  it("uses the local habit elsewhere", () => {
    expect(formatTimeOfDay(14, 30, "en")).toMatch(/2:30/);
    expect(formatTimeOfDay(14, 30, "sk")).toBe("14:30");
  });
});

describe("parsePreferences", () => {
  it("falls back to defaults on missing or broken data", () => {
    expect(parsePreferences(null)).toEqual(DEFAULT_PREFERENCES);
    expect(parsePreferences("{oops")).toEqual(DEFAULT_PREFERENCES);
  });

  it("keeps only known values", () => {
    expect(
      parsePreferences(
        JSON.stringify({ theme: "dark", textSize: "huge", dataSaver: true, city: "Paris" }),
      ),
    ).toEqual({ ...DEFAULT_PREFERENCES, theme: "dark", dataSaver: true, city: "Paris" });
  });
});

describe("DisplaySettings", () => {
  it("applies and stores the chosen theme and text size", async () => {
    renderWithProviders(<DisplaySettings />);

    await userEvent.click(screen.getByRole("button", { name: "Sombre" }));
    await userEvent.click(screen.getByRole("button", { name: "Très grand" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.dataset.textSize).toBe("xlarge");
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}");
    expect(stored).toMatchObject({ theme: "dark", textSize: "xlarge" });
    expect(screen.getByRole("button", { name: "Sombre" })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches the audio mode on", async () => {
    renderWithProviders(<DisplaySettings />);

    const audio = screen.getByRole("switch", { name: /Mode audio/ });
    expect(audio).toHaveAttribute("aria-checked", "false");
    await userEvent.click(audio);

    await waitFor(() => expect(audio).toHaveAttribute("aria-checked", "true"));
    expect(screen.getByRole("status")).toHaveTextContent("Réglage enregistré");
  });

  it("returns to the system theme", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ theme: "dark" }));
    renderWithProviders(<DisplaySettings />);

    await userEvent.click(await screen.findByRole("button", { name: "Comme le téléphone" }));
    expect(document.documentElement.dataset.theme).toBeUndefined();
  });
});
