import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRouter as getRouterMock } from "next/navigation";
import { describe, expect, it, vi } from "vitest";

import { ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { ConfirmEmail, ResetPassword } from "./email-link";
import { toInternational } from "./phone-field";
import { SignInFlow } from "./sign-in-flow";
import { WelcomeFlow } from "./welcome-flow";

// The mocked Next.js router is shared (see test/setup.ts).
const routerMock = getRouterMock() as unknown as { replace: ReturnType<typeof vi.fn> };

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
  it("creates an account, then asks to open the confirmation e-mail", async () => {
    const fetchMock = mockApi([
      { method: "POST", path: "/auth/signup", status: 202, body: { sent_to: "aw***@example.com" } },
    ]);
    renderWithProviders(<SignInFlow mode="signup" />);

    await userEvent.type(screen.getByLabelText("Ton prénom"), "Awa");
    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.type(screen.getByLabelText("Choisis un mot de passe"), "Rose-Hibiscus-2026");
    await userEvent.click(screen.getByRole("button", { name: "Afficher le mot de passe" }));
    expect(screen.getByLabelText("Choisis un mot de passe")).toHaveAttribute("type", "text");
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    expect(await screen.findByRole("heading", { name: "Regarde tes e-mails" })).toBeVisible();
    expect(screen.getByText(/On a envoyé un lien à aw\*\*\*@example.com/)).toBeVisible();
    expect(screen.getByRole("button", { name: /Renvoyer dans \d+ s/ })).toBeDisabled();
    expect(sentBody(fetchMock, "/auth/signup")).toEqual({
      email: "awa@example.com",
      password: "Rose-Hibiscus-2026",
      first_name: "Awa",
      locale: "fr",
    });
  });

  it("says why a password is refused, next to the field", async () => {
    mockApi([
      {
        method: "POST",
        path: "/auth/signup",
        status: 400,
        body: {
          code: "weak_password",
          message: "Choisis un mot de passe plus solide.",
          fields: { password: ["Ce mot de passe est trop courant."] },
        },
      },
    ]);
    renderWithProviders(<SignInFlow mode="signup" />);
    await userEvent.type(screen.getByLabelText("Ton prénom"), "Awa");
    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.type(screen.getByLabelText("Choisis un mot de passe"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Créer mon compte" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ce mot de passe est trop courant.");
    expect(screen.getByLabelText("Choisis un mot de passe")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("signs in and an existing account goes home", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/auth/password/login",
        body: { created: false, user: { ...ME, onboarding_required: false } },
      },
    ]);
    renderWithProviders(<SignInFlow />);

    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.type(screen.getByLabelText("Ton mot de passe"), "Rose-Hibiscus-2026");
    await userEvent.click(screen.getByRole("button", { name: "Me connecter" }));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(routerMock.replace.mock.calls[0]?.[0]).toBe("/fr");
    expect(sentBody(fetchMock, "/auth/password/login")).toEqual({
      identifier: "awa@example.com",
      password: "Rose-Hibiscus-2026",
    });
  });

  it("an address not confirmed yet is sent to its mailbox", async () => {
    mockApi([
      {
        method: "POST",
        path: "/auth/password/login",
        status: 403,
        body: { code: "email_not_confirmed", message: "Confirme d'abord ton adresse e-mail." },
      },
    ]);
    renderWithProviders(<SignInFlow />);
    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.type(screen.getByLabelText("Ton mot de passe"), "Rose-Hibiscus-2026");
    await userEvent.click(screen.getByRole("button", { name: "Me connecter" }));

    expect(await screen.findByRole("heading", { name: "Regarde tes e-mails" })).toBeVisible();
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  it("forgot password: the same answer, a link on its way", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/auth/password/forgot",
        status: 202,
        body: { sent_to: "aw***@example.com" },
      },
    ]);
    renderWithProviders(<SignInFlow />);
    await userEvent.click(screen.getByRole("button", { name: "Mot de passe oublié ?" }));
    await userEvent.type(screen.getByLabelText("Ton adresse e-mail"), "awa@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Recevoir le lien" }));

    expect(await screen.findByRole("heading", { name: "Lien envoyé" })).toBeVisible();
    expect(sentBody(fetchMock, "/auth/password/forgot")).toEqual({ email: "awa@example.com" });
  });
});

describe("Links of the e-mails", () => {
  it("the confirmation link signs in and opens the welcome screens", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/auth/email/confirm",
        status: 201,
        body: { created: true, user: ME },
      },
      { method: "PATCH", path: "/me", body: ME },
    ]);
    renderWithProviders(<ConfirmEmail token="abc:def" />);

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(String(routerMock.replace.mock.calls[0]?.[0])).toContain("/welcome");
    expect(sentBody(fetchMock, "/auth/email/confirm")).toEqual({ token: "abc:def" });
  });

  it("an old confirmation link says what to do", async () => {
    mockApi([
      {
        method: "POST",
        path: "/auth/email/confirm",
        status: 400,
        body: { code: "invalid_link", message: "Ce lien ne fonctionne plus." },
      },
    ]);
    renderWithProviders(<ConfirmEmail token="old" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Ce lien ne fonctionne plus.");
    expect(screen.getByRole("link", { name: "Me connecter" })).toBeVisible();
  });

  it("the reset link saves the new password and signs in", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/auth/password/reset",
        body: { created: false, user: { ...ME, onboarding_required: false } },
      },
    ]);
    renderWithProviders(<ResetPassword token="abc:def" />);
    await userEvent.type(
      screen.getByLabelText("Choisis un mot de passe"),
      "Nouveau-Mot-De-Passe-9",
    );
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer et me connecter" }));

    await waitFor(() => expect(routerMock.replace).toHaveBeenCalled());
    expect(sentBody(fetchMock, "/auth/password/reset")).toEqual({
      token: "abc:def",
      password: "Nouveau-Mot-De-Passe-9",
    });
  });
});

describe("WelcomeFlow", () => {
  it("records a professional with her trades, language and city, then blooms", async () => {
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

    await userEvent.click(await screen.findByRole("button", { name: /Je propose mes services/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Tresses" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    expect(screen.getByRole("heading", { name: "Ta langue" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    expect(screen.getByRole("heading", { name: "Ta ville et ton numéro" })).toBeVisible();
    await userEvent.type(screen.getByRole("combobox", { name: "Ta ville" }), "Abomey-Calavi");
    expect(screen.getByRole("button", { name: "C'est parti" })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText("Jour"), "12");
    await userEvent.selectOptions(screen.getByLabelText("Mois"), "4");
    await userEvent.selectOptions(screen.getByLabelText("Année"), "1995");
    expect(screen.getByRole("button", { name: "C'est parti" })).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /J'accepte les conditions/ }));
    await userEvent.click(screen.getByRole("button", { name: "C'est parti" }));

    expect(await screen.findByRole("img", { name: "Bienvenue !" })).toBeInTheDocument();
    expect(sentBody(fetchMock, "/me/onboarding")).toEqual({
      mode: "pro",
      birth_date: "1995-04-12",
      trades: ["braids"],
      language: "en",
      city: "Abomey-Calavi",
      accept_terms: true,
    });
  });

  it("needs a trade before a professional can continue", async () => {
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
