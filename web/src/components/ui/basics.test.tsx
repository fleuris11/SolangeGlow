import { MapPin, Package } from "@phosphor-icons/react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/render";

import { Badge } from "./badge";
import { Button } from "./button";
import { Chip } from "./chip";
import { EmptyState } from "./empty-state";
import { IconLabel } from "./icon-label";
import { Skeleton } from "./skeleton";

describe("Button", () => {
  it("is a real button with its label and calls onClick", async () => {
    const onClick = vi.fn();
    renderWithProviders(<Button onClick={onClick}>Réserver samedi 10 h</Button>);

    const button = screen.getByRole("button", { name: "Réserver samedi 10 h" });
    expect(button).toHaveAttribute("type", "button");
    await userEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("keeps the icon out of the accessible name", () => {
    renderWithProviders(<Button icon={<MapPin data-testid="icon" />}>Itinéraire</Button>);

    expect(screen.getByRole("button", { name: "Itinéraire" })).toBeInTheDocument();
    expect(screen.getByTestId("icon").parentElement).toHaveAttribute("aria-hidden");
  });

  it("renders its child with button styles when asChild", () => {
    renderWithProviders(
      <Button asChild>
        <a href="https://wa.me/2290197000000">WhatsApp</a>
      </Button>,
    );

    const link = screen.getByRole("link", { name: "WhatsApp" });
    expect(link).toHaveClass("rounded-full");
  });

  it("cannot be clicked when disabled", async () => {
    const onClick = vi.fn();
    renderWithProviders(
      <Button disabled onClick={onClick}>
        Payer
      </Button>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Payer" }));
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("IconLabel", () => {
  it("always shows the word next to a hidden icon", () => {
    renderWithProviders(<IconLabel icon={<MapPin data-testid="icon" />}>Cotonou</IconLabel>);

    expect(screen.getByText("Cotonou")).toBeVisible();
    expect(screen.getByTestId("icon").parentElement).toHaveAttribute("aria-hidden");
  });
});

describe("Chip", () => {
  it("exposes its on/off state", async () => {
    const onClick = vi.fn();
    const { rerender } = renderWithProviders(<Chip onClick={onClick}>Tresses</Chip>);

    const chip = screen.getByRole("button", { name: "Tresses" });
    expect(chip).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(chip);
    expect(onClick).toHaveBeenCalledOnce();

    rerender(<Chip selected>Tresses</Chip>);
    expect(screen.getByRole("button", { name: "Tresses" })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("Badge", () => {
  it.each(["glow", "star", "icon", "verified"] as const)("shows a word for %s", (tone) => {
    renderWithProviders(<Badge tone={tone}>Niveau</Badge>);
    expect(screen.getByText("Niveau")).toBeInTheDocument();
  });
});

describe("Skeleton", () => {
  it("is hidden from assistive technologies", () => {
    const { container } = renderWithProviders(<Skeleton className="h-4" />);
    expect(container.firstChild).toHaveAttribute("aria-hidden");
  });
});

describe("EmptyState", () => {
  it("shows a title, an invitation and an action", () => {
    renderWithProviders(
      <EmptyState
        icon={<Package />}
        title="Aucune commande"
        description="Découvre les boutiques près de toi."
        action={<Button>Voir les boutiques</Button>}
      />,
    );

    expect(screen.getByRole("heading", { name: "Aucune commande" })).toBeInTheDocument();
    expect(screen.getByText("Découvre les boutiques près de toi.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Voir les boutiques" })).toBeInTheDocument();
  });
});
