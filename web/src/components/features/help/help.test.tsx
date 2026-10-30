import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { HelpContact } from "./help-contact";
import { RichText } from "./rich-text";

afterEach(() => vi.unstubAllGlobals());

const faq = {
  id: "8a0f6c1e-6a9b-4d7c-9a51-3f5f0c2a1b11",
  topic: "booking",
  question: "Comment annuler un rendez-vous ?",
  answer: "Ouvre « Mes rendez-vous », puis « Annuler ».",
};

describe("HelpContact", () => {
  it("shows the answers of the FAQ first, then sends the question to the team", async () => {
    const api = mockApi([
      { method: "POST", path: "/help/suggest", body: { answer: null, faq: [faq] } },
      {
        method: "POST",
        path: "/help/tickets",
        status: 201,
        body: { reference: "T-ABC123", status: "new" },
      },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<HelpContact searchIcon={null} sendIcon={null} />);

    await user.type(screen.getByLabelText("Ta question"), "Annuler mon rendez-vous");
    await user.click(screen.getByRole("button", { name: "Chercher une réponse" }));
    expect(await screen.findByText(faq.question)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Non, écrire à l'équipe" }));
    await user.type(screen.getByLabelText("Ton prénom"), "Awa");
    await user.type(screen.getByLabelText("Ton e-mail"), "awa@example.com");
    await user.click(screen.getByRole("button", { name: "Envoyer ma question" }));

    expect(await screen.findByText("Question envoyée")).toBeInTheDocument();
    expect(screen.getByText(/T-ABC123/)).toBeInTheDocument();
    expect(sentBody(api, "/help/tickets")).toMatchObject({
      message: "Annuler mon rendez-vous",
      name: "Awa",
      email: "awa@example.com",
    });
  });
});

describe("RichText", () => {
  it("shows titles, lists and paragraphs as text, never as HTML", () => {
    renderWithProviders(<RichText text={"# Objet\n\n- un\n- deux\n\nLigne <b>1</b>\nLigne 2"} />);
    expect(screen.getByRole("heading", { name: "Objet" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText(/Ligne <b>1<\/b>/)).toBeInTheDocument();
  });
});
