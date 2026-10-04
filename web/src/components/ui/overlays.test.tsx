import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/render";

import { BottomNav } from "./bottom-nav";
import { Button } from "./button";
import { LocaleSwitcher } from "./locale-switcher";
import { Sheet } from "./sheet";
import { useToast } from "./toast";

describe("Sheet", () => {
  it("is a titled dialog that closes with the close button", async () => {
    const onOpenChange = vi.fn();
    renderWithProviders(
      <Sheet open onOpenChange={onOpenChange} title="Choisis ta ville">
        <p>Cotonou</p>
      </Sheet>,
    );

    expect(screen.getByRole("dialog", { name: "Choisis ta ville" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Fermer" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("closes with Escape", async () => {
    const onOpenChange = vi.fn();
    renderWithProviders(
      <Sheet open onOpenChange={onOpenChange} title="Choisis ta ville">
        <p>Cotonou</p>
      </Sheet>,
    );

    await userEvent.keyboard("{Escape}");
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

function ToastDemo() {
  const toast = useToast();
  return <Button onClick={() => toast("Publié")}>Publier</Button>;
}

describe("Toast", () => {
  it("announces the message politely, then disappears", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderWithProviders(<ToastDemo />);

    await user.click(screen.getByRole("button", { name: "Publier" }));
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveTextContent("Publié");

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(region).not.toHaveTextContent("Publié");
    vi.useRealTimers();
  });
});

describe("BottomNav", () => {
  it("has five entries with words and marks the current page", () => {
    renderWithProviders(<BottomNav />);

    const nav = screen.getByRole("navigation", { name: "Menu principal" });
    const links = nav.querySelectorAll("a");
    expect([...links].map((link) => link.textContent)).toEqual([
      "Accueil",
      "Explorer",
      "Publier",
      "Messages",
      "Moi",
    ]);
    expect(screen.getByRole("link", { name: "Explorer" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Accueil" })).not.toHaveAttribute("aria-current");
  });
});

describe("LocaleSwitcher", () => {
  it("offers each language in its own language, keeping the page", () => {
    renderWithProviders(<LocaleSwitcher />);

    const english = screen.getByRole("link", { name: "English" });
    expect(english).toHaveAttribute("lang", "en");
    expect(english.getAttribute("href")).toBe("/en/explore");
    expect(screen.getByRole("link", { name: "Français" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: "Slovenčina" })).toBeInTheDocument();
  });
});
