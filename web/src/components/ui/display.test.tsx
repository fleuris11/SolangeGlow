import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { STORAGE_KEY } from "@/lib/preferences/preferences";
import messages from "@/messages/fr.json";
import { renderWithProviders } from "@/test/render";

import { Avatar } from "./avatar";
import { Bloom } from "./bloom";
import { PriceTag } from "./price-tag";
import { SpeakButton } from "./speak-button";

describe("PriceTag", () => {
  it("shows complete, explicit prices", () => {
    const { container } = renderWithProviders(
      <>
        <PriceTag amountMinor={15000} currency="XOF" />
        <PriceTag amountMinor={2500} currency="EUR" />
        <PriceTag amountMinor={8000} currency="XOF" prefix="dès" />
      </>,
    );

    const prices = [...container.querySelectorAll("span.font-bold")].map((el) => el.textContent);
    expect(prices).toEqual(["15 000 FCFA", "25,00 €", "dès 8 000 FCFA"]);
  });
});

describe("Avatar", () => {
  it("falls back to initials with the name as accessible label", () => {
    renderWithProviders(<Avatar name="Sènami Hounkpè" />);

    const avatar = screen.getByRole("img", { name: "Sènami Hounkpè" });
    expect(avatar).toHaveTextContent("SH");
  });

  it("draws the Glow halo around the petal when asked", () => {
    const { container } = renderWithProviders(<Avatar name="Aïcha" halo />);

    expect(container.querySelector("[data-halo]")).not.toBeNull();
    expect(container.querySelectorAll(".petal").length).toBeGreaterThanOrEqual(2);
  });

  it("uses a custom picture when there is no photo", () => {
    renderWithProviders(<Avatar name="Gloria" picture={<svg data-testid="portrait" />} />);

    expect(screen.getByRole("img", { name: "Gloria" })).toContainElement(
      screen.getByTestId("portrait"),
    );
  });
});

describe("Bloom", () => {
  it("announces the success and vibrates lightly", () => {
    const vibrate = vi.fn();
    Object.defineProperty(navigator, "vibrate", { value: vibrate, configurable: true });

    renderWithProviders(<Bloom label="Paiement reçu" />);

    expect(screen.getByRole("img", { name: "Paiement reçu" })).toBeInTheDocument();
    expect(vibrate).toHaveBeenCalledWith(30);
  });
});

describe("SpeakButton", () => {
  const speakMock = vi.fn();
  const cancelMock = vi.fn();

  function installSpeech() {
    vi.stubGlobal("speechSynthesis", { speak: speakMock, cancel: cancelMock, getVoices: () => [] });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        lang = "";
        rate = 1;
        voice = null;
        onend: (() => void) | null = null;
        onerror: (() => void) | null = null;
        constructor(public text: string) {}
      },
    );
  }

  afterEach(() => {
    vi.unstubAllGlobals();
    speakMock.mockReset();
  });

  it("is hidden while the audio mode is off", () => {
    installSpeech();
    renderWithProviders(<SpeakButton text="Bonjour" />);

    expect(screen.queryByRole("button")).toBeNull();
  });

  it("reads the text in French when the audio mode is on", async () => {
    installSpeech();
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ audioMode: true }));
    renderWithProviders(<SpeakButton text="Ton code de réception" />);

    const button = await screen.findByRole("button", {
      name: messages.audio.listenTo.replace("{text}", "Ton code de réception"),
    });
    await userEvent.click(button);

    expect(speakMock).toHaveBeenCalledOnce();
    const utterance = speakMock.mock.calls[0]?.[0] as { text: string; lang: string };
    expect(utterance.text).toBe("Ton code de réception");
    expect(utterance.lang).toBe("fr-FR");
  });

  it("is hidden when the browser cannot speak", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ audioMode: true }));
    await act(async () => {
      renderWithProviders(<SpeakButton text="Bonjour" always />);
    });

    expect(screen.queryByRole("button")).toBeNull();
  });
});
