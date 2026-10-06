import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { NotificationBell } from "@/components/shell/notification-bell";
import { called, ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { NotificationsContent } from "./notifications-content";

const SIGNED_IN = { ...ME, onboarding_required: false, email: "awa@example.com" };

const PAGE = {
  next: null,
  previous: null,
  results: [
    {
      id: "n1",
      event_key: "account.welcome",
      title: "Bienvenue sur Solange Glow !",
      body: "Ton compte est prêt.",
      link: "/",
      read: false,
      created_at: new Date().toISOString(),
    },
    {
      id: "n2",
      event_key: "system.test",
      title: "Test réussi",
      body: "",
      link: "/notifications",
      read: true,
      created_at: new Date(Date.now() - 86_400_000).toISOString(),
    },
  ],
};

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

describe("NotificationsContent", () => {
  it("invites visitors to sign in", async () => {
    mockApi([]);
    renderWithProviders(<NotificationsContent />);

    expect(await screen.findByRole("link", { name: "Me connecter" })).toHaveAttribute(
      "href",
      "/fr/auth",
    );
  });

  it("lists notifications, new ones first marked, and marks everything as read", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: SIGNED_IN },
      { path: "/notifications", body: PAGE },
      { path: "/notifications/unread-count", body: { unread: 1 } },
      { method: "POST", path: "/notifications/read", body: { unread: 0 } },
    ]);
    renderWithProviders(<NotificationsContent />);

    const item = await screen.findByRole("button", { name: /Bienvenue sur Solange Glow/ });
    expect(within(item).getByText("Nouveau")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tout marquer comme lu" }));

    await waitFor(() => expect(called(fetchMock, "/notifications/read", "POST")).toBe(true));
    expect(sentBody(fetchMock, "/notifications/read")).toEqual({});
  });

  it("saves the quiet hours and the e-mail channel", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: SIGNED_IN },
      { path: "/notifications", body: { next: null, previous: null, results: [] } },
      { method: "PATCH", path: "/me", body: SIGNED_IN },
    ]);
    renderWithProviders(<NotificationsContent />);

    expect(await screen.findByText("Aucune alerte pour l'instant")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: /Par e-mail/ }));
    await waitFor(() => expect(sentBody(fetchMock, "/me")).toEqual({ notify_email: false }));

    const from = screen.getByLabelText("De");
    await userEvent.clear(from);
    await userEvent.type(from, "21:00");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer les heures" }));

    await waitFor(() =>
      expect(sentBody(fetchMock, "/me", 1)).toEqual({
        quiet_hours_start: "21:00",
        quiet_hours_end: "07:00",
      }),
    );
  });

  it("explains when this browser cannot show phone alerts", async () => {
    signIn();
    mockApi([
      { path: "/me", body: SIGNED_IN },
      { path: "/notifications", body: { next: null, previous: null, results: [] } },
    ]);
    renderWithProviders(<NotificationsContent />);

    const push = await screen.findByRole("switch", { name: /Alertes sur ce téléphone/ });
    await waitFor(() => expect(push).toBeDisabled());
    expect(push).toHaveTextContent("Ce navigateur ne permet pas les alertes");
  });
});

describe("NotificationBell", () => {
  it("shows the number of unread notifications", async () => {
    signIn();
    mockApi([
      { path: "/me", body: SIGNED_IN },
      { path: "/notifications/unread-count", body: { unread: 3 } },
    ]);
    renderWithProviders(<NotificationBell />);

    expect(await screen.findByRole("link", { name: "Alertes : 3 nouvelles" })).toHaveAttribute(
      "href",
      "/fr/notifications",
    );
  });

  it("is a plain link for visitors", async () => {
    mockApi([]);
    renderWithProviders(<NotificationBell />);

    expect(await screen.findByRole("link", { name: "Alertes" })).toBeInTheDocument();
  });
});
