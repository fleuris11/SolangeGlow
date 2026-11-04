import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  applyPreferences,
  DEFAULT_PREFERENCES,
  parsePreferences,
} from "@/lib/preferences/preferences";
import { prefersReducedMotion } from "@/lib/motion";
import { renderWithProviders } from "@/test/render";

import { AnimatedNumber } from "./animated-number";
import { BeforeAfterSlider } from "./before-after-slider";
import { EditorialSection } from "./editorial-section";
import { ImageGallery } from "./image-gallery";
import { Marquee } from "./marquee";
import { PhotoCard } from "./photo-card";
import { Sheet } from "./sheet";
import { StoryViewer } from "./story-viewer";

const STORIES = [
  { id: "a", src: "/a.webp", alt: "Première", caption: "Une" },
  { id: "b", src: "/b.webp", alt: "Deuxième", caption: "Deux" },
];

describe("reduced animations", () => {
  it("is read from the stored preferences and shown on <html>", () => {
    expect(parsePreferences(JSON.stringify({ reducedMotion: true })).reducedMotion).toBe(true);
    expect(parsePreferences("{}").reducedMotion).toBe(false);
    applyPreferences({ ...DEFAULT_PREFERENCES, reducedMotion: true });
    expect(document.documentElement.dataset.motion).toBe("reduced");
    expect(prefersReducedMotion()).toBe(true);
    applyPreferences(DEFAULT_PREFERENCES);
    expect(document.documentElement.dataset.motion).toBe("full");
  });
});

describe("EditorialSection", () => {
  it("repaints the tokens only for a night section", () => {
    const { container, rerender } = renderWithProviders(<EditorialSection ambiance="nuit" />);
    expect(container.querySelector("section")).toHaveAttribute("data-ambiance", "nuit");
    rerender(<EditorialSection ambiance="poudre" />);
    expect(container.querySelector("section")).not.toHaveAttribute("data-ambiance");
  });
});

describe("PhotoCard", () => {
  it("names the photo and carries its words", () => {
    renderWithProviders(
      <PhotoCard src="/a.webp" alt="Une femme" title="Tresses" subtitle="15 000 FCFA" />,
    );
    expect(screen.getByRole("img", { name: "Une femme" })).toBeInTheDocument();
    expect(screen.getByText("15 000 FCFA")).toBeInTheDocument();
  });
});

describe("BeforeAfterSlider", () => {
  it("is a real slider that moves the clip of the top picture", () => {
    renderWithProviders(
      <BeforeAfterSlider before="/a.webp" after="/b.webp" beforeAlt="Avant" afterAlt="Après" />,
    );
    const slider = screen.getByRole("slider", { name: "Comparer avant et après" });
    fireEvent.change(slider, { target: { value: "20" } });
    expect(screen.getByRole("img", { name: "Avant" }).style.clipPath).toContain("80%");
  });
});

describe("ImageGallery", () => {
  it("says where we are", () => {
    renderWithProviders(
      <ImageGallery
        images={[
          { src: "/a.webp", alt: "A" },
          { src: "/b.webp", alt: "B" },
        ]}
      />,
    );
    expect(screen.getByRole("list", { name: "Photo 1 sur 2" })).toBeInTheDocument();
  });

  it("has no dots for one photo", () => {
    renderWithProviders(<ImageGallery images={[{ src: "/a.webp", alt: "A" }]} />);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});

describe("Marquee", () => {
  it("hides its seamless copy from assistive technologies", () => {
    renderWithProviders(
      <Marquee label="Métiers">
        <button type="button">Tresses</button>
      </Marquee>,
    );
    expect(screen.getByRole("group", { name: "Métiers" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Tresses" })).toHaveLength(1);
  });
});

describe("StoryViewer", () => {
  it("never advances by itself, and closes after the last story", () => {
    const onOpenChange = vi.fn();
    renderWithProviders(
      <StoryViewer stories={STORIES} open onOpenChange={onOpenChange} title="Stories" />,
    );
    expect(screen.getByRole("progressbar", { name: "Story 1 sur 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Précédente" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Suivante" }));
    expect(screen.getByText("Deux")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Terminer" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

describe("Sheet", () => {
  it("closes on a flick of the handle", () => {
    const onOpenChange = vi.fn();
    renderWithProviders(
      <Sheet open onOpenChange={onOpenChange} title="Feuille">
        Contenu
      </Sheet>,
    );
    const handle = screen.getByRole("dialog").firstElementChild!;
    fireEvent.pointerDown(handle, { pointerId: 1, clientY: 100 });
    fireEvent.pointerMove(handle, { pointerId: 1, clientY: 300 });
    fireEvent.pointerUp(handle, { pointerId: 1, clientY: 300 });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

describe("AnimatedNumber", () => {
  it("formats the number in the language of the page", () => {
    renderWithProviders(<AnimatedNumber value={1240} />);
    expect(screen.getByText(/1.240/)).toBeInTheDocument();
  });
});
