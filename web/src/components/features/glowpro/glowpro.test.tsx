import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { MyGlowPro } from "@/lib/api/glowpro";
import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { CampaignsScreen } from "./campaigns-screen";
import { DashboardScreen } from "./dashboard-screen";
import { PlanScreen } from "./plan-screen";

const FREE = {
  key: "free",
  name: "Gratuit",
  description: "",
  features: [],
  limits: { staff: 2, campaigns_per_month: 0 },
  trial_days: 0,
  price_minor: null,
  currency: "",
  is_default: true,
};
const PREMIUM = {
  ...FREE,
  key: "premium",
  name: "Premium",
  features: [
    "extra_staff",
    "client_file",
    "stock",
    "dashboard_full",
    "campaigns",
    "widget",
    "einvoice",
  ],
  limits: { campaigns_per_month: 4 },
  trial_days: 30,
  price_minor: 9900,
  currency: "XOF",
  is_default: false,
} as MyGlowPro["plans"][number];

function myPlan(overrides: Partial<MyGlowPro> = {}): MyGlowPro {
  return {
    current: FREE as MyGlowPro["current"],
    subscription: {
      status: "ended",
      plan: "free",
      trial_used: false,
      current_period_end: null,
      grace_until: null,
      cancel_at_period_end: false,
      payment_due: false,
    },
    plans: [FREE as MyGlowPro["plans"][number], PREMIUM],
    usage: { staff: 1, staff_limit: 2 },
    invoices: [],
    is_paying: false,
    ...overrides,
  };
}

describe("PlanScreen", () => {
  it("shows the free plan and starts the trial", async () => {
    const fetchMock = mockApi([
      { path: "/me/glowpro", body: myPlan() },
      {
        method: "POST",
        path: "/me/glowpro/trial",
        body: myPlan({ current: PREMIUM as MyGlowPro["current"] }),
      },
    ]);
    renderWithProviders(<PlanScreen />);
    expect(await screen.findByText("Tu utilises l'offre gratuite.")).toBeVisible();
    expect(screen.getByText("Équipe : 1 sur 2 personnes en plus de toi")).toBeVisible();
    expect(screen.getByRole("rowheader", { name: "Stock avec scan du code-barres" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /Essayer gratuitement 30 jours/ }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/glowpro/trial")).toEqual({ plan: "premium" }),
    );
  });
});

describe("Premium screens", () => {
  it("offer the trial to a free pro", async () => {
    mockApi([{ path: "/me/glowpro", body: myPlan() }]);
    renderWithProviders(<CampaignsScreen />);
    expect(await screen.findByRole("heading", { name: "Fais revenir tes clientes" })).toBeVisible();
  });

  it("the free dashboard shows the month in two numbers", async () => {
    mockApi([
      { path: "/me/glowpro", body: myPlan() },
      {
        path: "/me/dashboard",
        body: {
          level: "basic",
          currency: "XOF",
          basic: { start: "2030-01-01", end: "2030-01-07", turnover_minor: 45000, appointments: 3 },
          current: null,
          previous: null,
        },
      },
    ]);
    renderWithProviders(<DashboardScreen />);
    expect(await screen.findByText(/45\s000 FCFA/)).toBeVisible();
    expect(screen.getByText("3")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Tout comprendre de ton activité" })).toBeVisible();
  });
});
