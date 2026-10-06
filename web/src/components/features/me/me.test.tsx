import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter as getRouterMock } from "next/navigation";
import { describe, expect, it, vi } from "vitest";

import { called, ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { MeContent } from "./me-content";

// The signed-in screens are loaded on demand (next/dynamic): load them before the tests
// so that the first render does not wait for the module graph.
import "./account-settings";
import "./guest-card";
import "./profile-form";
import "@/components/features/settings/display-settings";

const routerMock = getRouterMock() as unknown as { replace: ReturnType<typeof vi.fn> };
const SIGNED_IN = { ...ME, first_name: "Awa", onboarding_required: false };

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

describe("MeContent for a visitor", () => {
  it("invites to sign in and offers booking without an account", async () => {
    mockApi([]);
    renderWithProviders(<MeContent />);

    expect(await screen.findByRole("link", { name: "Me connecter ou m'inscrire" })).toHaveAttribute(
      "href",
      "/fr/auth",
    );
    expect(
      await screen.findByRole("heading", { name: "Réserver sans compte" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Affichage" })).toBeInTheDocument();
  });

  it("registers a guest with a first name and a number", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/guest",
        status: 201,
        body: { id: "g1", first_name: "Awa", phone: "+2290197123456" },
      },
    ]);
    renderWithProviders(<MeContent />);

    const card = (await screen.findByRole("heading", { name: "Réserver sans compte" })).closest(
      "section",
    ) as HTMLElement;
    await userEvent.type(within(card).getByLabelText("Ton prénom"), "Awa");
    await userEvent.type(within(card).getByLabelText("Ton numéro de téléphone"), "0197123456");
    await userEvent.click(within(card).getByRole("button", { name: "Continuer en invitée" }));

    expect(
      await within(card).findByText("Tu es enregistrée comme invitée : Awa, +2290197123456."),
    ).toBeInTheDocument();
    expect(sentBody(fetchMock, "/guest")).toEqual({ first_name: "Awa", phone: "+2290197123456" });
  });
});

describe("MeContent when signed in", () => {
  it("shows and saves the profile", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: SIGNED_IN },
      {
        path: "/countries",
        body: [{ code: "BJ", name: "Bénin", phone_prefix: "+229", default_currency: "XOF" }],
      },
      { method: "PATCH", path: "/me", body: { ...SIGNED_IN, city: "Cotonou" } },
    ]);
    renderWithProviders(<MeContent />);

    expect(await screen.findByRole("heading", { name: "Awa" })).toBeInTheDocument();
    expect(screen.getAllByText("+2290197123456").length).toBeGreaterThan(0);

    await userEvent.type(screen.getByLabelText("Ville"), "Cotonou");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(sentBody(fetchMock, "/me")).toMatchObject({ city: "Cotonou" }));
    expect(await screen.findByText("Profil enregistré")).toBeInTheDocument();
  });

  it("signs out on every device", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: SIGNED_IN },
      { method: "POST", path: "/auth/logout-all", body: { status: "ok" } },
    ]);
    renderWithProviders(<MeContent />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Me déconnecter de tous mes appareils" }),
    );

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(called(fetchMock, "/auth/logout-all", "POST")).toBe(true);
  });

  it("deletes the account only after confirmation", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: SIGNED_IN },
      {
        method: "DELETE",
        path: "/me",
        status: 202,
        body: { erase_after: "2026-11-04T10:00:00Z" },
      },
    ]);
    renderWithProviders(<MeContent />);

    await userEvent.click(await screen.findByRole("button", { name: "Supprimer mon compte" }));
    const dialog = await screen.findByRole("dialog", { name: "Supprimer ton compte ?" });
    expect(called(fetchMock, "/me", "DELETE")).toBe(false);

    await userEvent.click(
      within(dialog).getByRole("button", { name: "Oui, supprimer mon compte" }),
    );

    await waitFor(() => expect(sentBody(fetchMock, "/me")).toEqual({ confirm: true }));
    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(await screen.findByText(/sera effacé le/)).toBeInTheDocument();
  });
});
