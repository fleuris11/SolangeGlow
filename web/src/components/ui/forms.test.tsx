import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/render";

import { CodeInput } from "./code-input";
import { Input } from "./input";
import { Stepper } from "./stepper";

describe("Input", () => {
  it("links the label and the hint to the field", () => {
    renderWithProviders(<Input label="Ton prénom" hint="Les pros le verront." />);

    const input = screen.getByLabelText("Ton prénom");
    expect(input).toHaveAccessibleDescription("Les pros le verront.");
    expect(input).not.toHaveAttribute("aria-invalid");
  });

  it("explains an error and marks the field invalid", () => {
    renderWithProviders(
      <Input label="Ton numéro" error="Ce numéro est incomplet. Vérifie les 10 chiffres." />,
    );

    const input = screen.getByLabelText("Ton numéro");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Ce numéro est incomplet. Vérifie les 10 chiffres.");
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("CodeInput", () => {
  it("has one labelled box per digit", () => {
    renderWithProviders(<CodeInput label="Code reçu" />);

    expect(screen.getAllByRole("textbox")).toHaveLength(6);
    expect(screen.getByLabelText("Chiffre 1 sur 6")).toHaveAttribute(
      "autocomplete",
      "one-time-code",
    );
  });

  it("moves forward while typing and completes the code", async () => {
    const onComplete = vi.fn();
    renderWithProviders(<CodeInput label="Code reçu" onComplete={onComplete} />);

    await userEvent.click(screen.getByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("482913");

    expect(onComplete).toHaveBeenCalledWith("482913");
    expect(screen.getByLabelText("Chiffre 6 sur 6")).toHaveValue("3");
  });

  it("fills every box from a pasted code, ignoring spaces", () => {
    const onComplete = vi.fn();
    renderWithProviders(<CodeInput label="Code reçu" onComplete={onComplete} />);

    fireEvent.paste(screen.getByLabelText("Chiffre 1 sur 6"), {
      clipboardData: { getData: () => "482 913" },
    });

    expect(onComplete).toHaveBeenCalledWith("482913");
  });

  it("goes back with Backspace on an empty box", async () => {
    renderWithProviders(<CodeInput label="Code reçu" />);

    await userEvent.click(screen.getByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("12{Backspace}{Backspace}");

    expect(screen.getByLabelText("Chiffre 2 sur 6")).toHaveValue("");
    expect(screen.getByLabelText("Chiffre 1 sur 6")).toHaveFocus();
  });

  it("refuses letters", async () => {
    renderWithProviders(<CodeInput label="Code reçu" />);

    await userEvent.click(screen.getByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("a");

    expect(screen.getByLabelText("Chiffre 1 sur 6")).toHaveValue("");
  });

  it("shows the error message", () => {
    renderWithProviders(<CodeInput label="Code reçu" error="Le code ne correspond pas." />);

    expect(screen.getByRole("alert")).toHaveTextContent("Le code ne correspond pas.");
  });
});

describe("Stepper", () => {
  it("says where we are and allows going back", async () => {
    const onBack = vi.fn();
    renderWithProviders(<Stepper current={2} total={3} onBack={onBack} />);

    expect(screen.getByText("Étape 2 sur 3")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retour" }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it("hides the back button on the first step", () => {
    renderWithProviders(<Stepper current={1} total={3} onBack={() => {}} />);

    expect(screen.queryByRole("button", { name: "Retour" })).toBeNull();
  });
});
