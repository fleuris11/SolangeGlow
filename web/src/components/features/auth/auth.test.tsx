import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter as getRouterMock } from "next/navigation";
import { describe, expect, it, vi } from "vitest";

import { STORAGE_KEY } from "@/lib/preferences/preferences";
import { ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { toInternational } from "./phone-field";
import { SignInFlow } from "./sign-in-flow";
import { WelcomeFlow } from "./welcome-flow";

// The mocked Next.js router is shared (see test/setup.ts).
const routerMock = getRouterMock() as unknown as { replace: ReturnType<typeof vi.fn> };

const CODE_SENT = {
  challenge_id: "c1",
  channel: "whatsapp",
  resend_after: 60,
  expires_in: 600,
};

describe("toInternational", () => {
  it.each([
    ["BJ", "01 97 12 34 56", "+2290197123456"],
    ["FR", "06 12 34 56 78", "+33612345678"],
    ["FR", "+33 6 12 34 56 78", "+33612345678"],
    ["OTHER", "421 900 123 456", "+421900123456"],
  ])("%s %s → %s", (country, typed, expected) => {
    expect(toInternational(country, typed)).toBe(expected);
  });
});

describe("SignInFlow", () => {
  it("sends the code, then signs up and opens the welcome screens", async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ theme: "dark", city: "Paris" }));
    const fetchMock = mockApi([
      { method: "POST", path: "/auth/otp/request", status: 202, body: CODE_SENT },
      { method: "POST", path: "/auth/otp/verify", status: 201, body: { created: true, user: ME } },
      { method: "PATCH", path: "/me", body: { ...ME, theme: "dark", city: "Paris" } },
    ]);
    renderWithProviders(<SignInFlow />);

    await userEvent.type(screen.getByLabelText("Ton numéro de téléphone"), "01 97 12 34 56");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir mon code" }));

    expect(sentBody(fetchMock, "/auth/otp/request")).toEqual({
      phone: "+2290197123456",
      locale: "fr",
    });
    expect(
      await screen.findByText("Code envoyé par WhatsApp au +2290197123456."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Renvoyer dans \d+ s/ })).toBeDisabled();

    await userEvent.click(screen.getByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("482913");

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(String(routerMock.replace.mock.calls[0]?.[0])).toContain("/welcome");
    expect(sentBody(fetchMock, "/auth/otp/verify")).toMatchObject({
      challenge_id: "c1",
      code: "482913",
    });
    // Choices made as a visitor are kept in the new account.
    expect(sentBody(fetchMock, "/me")).toMatchObject({ theme: "dark", city: "Paris" });
  });

  it("explains a wrong code", async () => {
    mockApi([
      { method: "POST", path: "/auth/otp/request", status: 202, body: CODE_SENT },
      {
        method: "POST",
        path: "/auth/otp/verify",
        status: 400,
        body: {
          code: "invalid_code",
          message: "Le code ne correspond pas. Vérifie les 6 chiffres reçus.",
          attempts_left: 4,
        },
      },
    ]);
    renderWithProviders(<SignInFlow />);

    await userEvent.type(screen.getByLabelText("Ton numéro de téléphone"), "0197123456");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir mon code" }));
    await userEvent.click(await screen.findByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("000000");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le code ne correspond pas. Vérifie les 6 chiffres reçus.",
    );
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  it("shows a rate limit message and keeps the person on the first step", async () => {
    mockApi([
      {
        method: "POST",
        path: "/auth/otp/request",
        status: 429,
        body: { code: "too_many_requests", message: "Attends un peu.", retry_after: 3600 },
      },
    ]);
    renderWithProviders(<SignInFlow />);

    await userEvent.type(screen.getByLabelText("Ton numéro de téléphone"), "0197123456");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir mon code" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Attends un peu.");
    expect(screen.getByLabelText("Ton numéro de téléphone")).toBeInTheDocument();
  });

  it("signs in with e-mail and an existing account goes home", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/auth/otp/request",
        status: 202,
        body: { ...CODE_SENT, channel: "email" },
      },
      {
        method: "POST",
        path: "/auth/otp/verify",
        body: { created: false, user: { ...ME, onboarding_required: false } },
      },
    ]);
    renderWithProviders(<SignInFlow />);

    await userEvent.click(screen.getByRole("button", { name: "E-mail" }));
    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir mon code" }));
    await userEvent.click(await screen.findByLabelText("Chiffre 1 sur 6"));
    await userEvent.keyboard("482913");

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(routerMock.replace.mock.calls[0]?.[0]).toBe("/fr");
    expect(sentBody(fetchMock, "/auth/otp/request")).toMatchObject({ email: "awa@example.com" });
  });
});

describe("WelcomeFlow", () => {
  it("records a pro with her trades, language and city, then blooms", async () => {
    document.cookie = "sg_signed_in=1; path=/";
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      {
        path: "/trades",
        body: [
          { key: "braids", name: "Tresses", icon: "braids" },
          { key: "makeup", name: "Maquillage", icon: "makeup" },
        ],
      },
      {
        method: "POST",
        path: "/me/onboarding",
        body: { ...ME, is_pro: true, onboarding_required: false },
      },
    ]);
    renderWithProviders(<WelcomeFlow />);

    await userEvent.click(await screen.findByRole("button", { name: /Je suis une pro/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Tresses" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    expect(screen.getByRole("heading", { name: "Ta langue" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    await userEvent.click(screen.getByRole("button", { name: "Abomey-Calavi" }));
    await userEvent.click(screen.getByRole("button", { name: "C'est parti" }));

    expect(await screen.findByRole("img", { name: "Bienvenue !" })).toBeInTheDocument();
    expect(sentBody(fetchMock, "/me/onboarding")).toEqual({
      mode: "pro",
      trades: ["braids"],
      language: "en",
      city: "Abomey-Calavi",
    });
  });

  it("needs a trade before a pro can continue", async () => {
    document.cookie = "sg_signed_in=1; path=/";
    mockApi([
      { path: "/me", body: ME },
      { path: "/trades", body: [{ key: "braids", name: "Tresses", icon: "braids" }] },
    ]);
    renderWithProviders(<WelcomeFlow as="pro" />);

    expect(await screen.findByRole("button", { name: "Tresses" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continuer" })).toBeDisabled();
  });

  it("sends visitors to the sign-in page", async () => {
    mockApi([]);
    renderWithProviders(<WelcomeFlow />);

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(String(routerMock.replace.mock.calls[0]?.[0])).toContain("/auth");
  });
});
