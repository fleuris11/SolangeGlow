import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { toIsoDate } from "@/components/features/auth/birth-date-field";
import { ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { ContactChange } from "./contact-change";

describe("ContactChange", () => {
  it("adds an e-mail after checking the code sent to it", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/me/contact",
        status: 202,
        body: { challenge_id: "c9", channel: "email", resend_after: 60, expires_in: 600 },
      },
      {
        method: "POST",
        path: "/me/contact/confirm",
        body: { ...ME, email: "awa@example.com" },
      },
    ]);
    renderWithProviders(<ContactChange me={{ ...ME, email: null } as never} />);

    await userEvent.click(screen.getByRole("button", { name: "Ajouter" }));
    await userEvent.type(
      await screen.findByLabelText("Ta nouvelle adresse e-mail"),
      "awa@example.com",
    );
    await userEvent.click(screen.getByRole("button", { name: "Recevoir le code" }));

    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/contact")).toEqual({
        email: "awa@example.com",
        locale: "fr",
      }),
    );
    await userEvent.click(await screen.findByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("482913");

    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/contact/confirm")).toEqual({
        challenge_id: "c9",
        code: "482913",
      }),
    );
    expect(await screen.findByText("E-mail enregistré")).toBeInTheDocument();
  });

  it("explains a number already used", async () => {
    mockApi([
      {
        method: "POST",
        path: "/me/contact",
        status: 400,
        body: { code: "contact_taken", message: "Ce numéro ou cet e-mail est déjà utilisé." },
      },
    ]);
    renderWithProviders(<ContactChange me={ME as never} />);

    await userEvent.click(screen.getAllByRole("button", { name: "Changer" })[0]!);
    await userEvent.type(await screen.findByLabelText("Ton numéro de téléphone"), "0196000000");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir le code" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("déjà utilisé");
  });
});

describe("toIsoDate", () => {
  it("builds the date and refuses impossible ones", () => {
    expect(toIsoDate({ day: "12", month: "4", year: "1995" })).toBe("1995-04-12");
    expect(toIsoDate({ day: "31", month: "2", year: "2001" })).toBeNull();
    expect(toIsoDate({ day: "", month: "2", year: "2001" })).toBeNull();
  });
});
