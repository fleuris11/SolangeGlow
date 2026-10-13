import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import type { Payment } from "@/lib/api/payments";
import { ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { CourierConfirm } from "./courier-confirm";
import { PaymentDetail } from "./payment-detail";
import { TestCheckout } from "./test-checkout";
import { WalletScreen } from "./wallet";

const person = (id: string, name: string) => ({
  id,
  name,
  photo: null,
  is_pro: id === "u2",
  pro_slug: id === "u2" ? "aicha" : null,
  verified: true,
});

const PAYMENT: Payment = {
  id: "p1",
  reference: "SG-ABCD2345",
  description: "Perruque lace frontale",
  purpose: "order",
  status: "held",
  role: "buyer",
  currency: "XOF",
  items_minor: 10_000,
  delivery_minor: 1_000,
  buyer_fee_minor: 330,
  total_minor: 11_330,
  commission_minor: null,
  seller_net_minor: null,
  refunded_minor: 0,
  delivery_mode: "seller",
  carrier: "",
  tracking_number: "",
  expected_delivery_at: null,
  delivered_at: null,
  delivery_proof: null,
  service_at: null,
  created_at: "2026-10-13T10:00:00Z",
  expires_at: null,
  paid_at: "2026-10-13T10:01:00Z",
  shipped_at: null,
  released_at: null,
  refunded_at: null,
  cancelled_at: null,
  end_reason: "",
  provider: "fake",
  checkout_url: "",
  buyer: person("u1", "Awa"),
  seller: person("u2", "Aïcha Tresses"),
  receipt_code: "482913",
  code_attempts_left: null,
  dispute: null,
  can: {
    pay: false,
    ship: false,
    deliver: false,
    confirm: false,
    cancel: true,
    dispute: true,
    new_code: true,
  },
};

const SELLER_VIEW: Payment = {
  ...PAYMENT,
  role: "seller",
  receipt_code: null,
  commission_minor: 0,
  seller_net_minor: 11_000,
  code_attempts_left: 5,
  can: { ...PAYMENT.can, confirm: true, ship: true, dispute: false, new_code: false },
};

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

beforeAll(async () => {
  await import("./payment-actions");
}, 30_000);

describe("PaymentDetail", () => {
  it("shows the client her code, the amounts and what she can do", async () => {
    signIn();
    mockApi([
      { path: "/me", body: ME },
      { path: "/payments/p1", body: PAYMENT },
    ]);
    renderWithProviders(<PaymentDetail paymentId="p1" />);
    expect(await screen.findByRole("heading", { name: "Perruque lace frontale" })).toBeVisible();
    const code = screen.getByRole("region", { name: "Ton code de réception" });
    expect(within(code).getByText("482 913")).toBeVisible();
    expect(screen.getByText("Vendu par Aïcha Tresses")).toBeVisible();
    expect(screen.getByText("Protection acheteur")).toBeVisible();
    expect(screen.getByText(/11\s?330/)).toBeVisible();
    expect(screen.queryByText("Commission Solange Glow")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Annuler ma commande/ })).toBeVisible();
  });

  it("opens a dispute with a reason", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      { path: "/payments/p1", body: PAYMENT },
      {
        method: "POST",
        path: "/payments/p1/dispute",
        status: 201,
        body: {
          ...PAYMENT,
          status: "disputed",
          dispute: {
            id: "d1",
            reason: "damaged",
            status: "open",
            description: "Abîmée",
            response_due_at: "2026-10-15T10:00:00Z",
            decision: null,
            refund_minor: 0,
            note: "",
            conversation_id: "c9",
            evidence: [],
          },
        },
      },
    ]);
    renderWithProviders(<PaymentDetail paymentId="p1" />);
    await userEvent.click(
      await screen.findByRole("button", { name: /Un problème avec ma commande/ }),
    );
    const send = screen.getByRole("button", { name: "Ouvrir le litige" });
    expect(send).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Abîmé" }));
    await userEvent.type(screen.getByLabelText("Explique en quelques mots"), "Abîmée");
    await userEvent.click(send);
    expect(await screen.findByRole("heading", { name: "Litige en cours" })).toBeVisible();
    expect(screen.getByRole("link", { name: /discussion à trois/ })).toHaveAttribute(
      "href",
      "/fr/messages/c9",
    );
    expect(sentBody(fetchMock, "/payments/p1/dispute")).toMatchObject({
      reason: "damaged",
      description: "Abîmée",
    });
  });

  it("lets the seller type the client's code", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      { path: "/payments/p1", body: SELLER_VIEW },
      {
        method: "POST",
        path: "/payments/p1/confirm",
        body: {
          ...SELLER_VIEW,
          status: "released",
          can: { ...SELLER_VIEW.can, confirm: false, ship: false },
        },
      },
    ]);
    renderWithProviders(<PaymentDetail paymentId="p1" />);
    expect(await screen.findByText("Pour toi")).toBeVisible();
    expect(screen.getByText("5 essais restants")).toBeVisible();
    const confirm = screen.getByRole("button", { name: "Valider le code" });
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Code à 6 chiffres"), "48a2913");
    await userEvent.click(confirm);
    expect(await screen.findByText("Terminé, argent versé")).toBeVisible();
    expect(sentBody(fetchMock, "/payments/p1/confirm")).toEqual({ code: "482913" });
  });
});

describe("TestCheckout", () => {
  it("answers like the bank would", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/payments/p1", body: { ...PAYMENT, status: "pending_payment", receipt_code: null } },
      { method: "POST", path: "/payments/p1/test-outcome", body: PAYMENT },
    ]);
    renderWithProviders(<TestCheckout paymentId="p1" />);
    expect(await screen.findByText(/aucun argent réel ne bouge/)).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /Paiement réussi/ }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/payments/p1/test-outcome")).toEqual({ outcome: "succeeded" }),
    );
  });
});

describe("CourierConfirm", () => {
  it("confirms the code without an account", async () => {
    mockApi([
      {
        path: "/payments/courier/tok",
        body: { reference: "SG-ABCD2345", description: "Perruque", seller: "Aïcha Tresses" },
      },
      { method: "POST", path: "/payments/courier/tok", status: 204 },
    ]);
    renderWithProviders(<CourierConfirm token="tok" />);
    expect(await screen.findByText("Commande SG-ABCD2345 de Aïcha Tresses")).toBeVisible();
    await userEvent.type(screen.getByLabelText("Code à 6 chiffres"), "482913");
    await userEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(await screen.findByText("C'est validé !")).toBeVisible();
  });

  it("explains a wrong code", async () => {
    mockApi([
      { path: "/payments/courier/tok", body: { reference: "R", description: "D", seller: "S" } },
      {
        method: "POST",
        path: "/payments/courier/tok",
        status: 400,
        body: { code: "wrong_code", message: "Ce code n'est pas le bon. Essais restants : 4." },
      },
    ]);
    renderWithProviders(<CourierConfirm token="tok" />);
    await userEvent.type(await screen.findByLabelText("Code à 6 chiffres"), "000000");
    await userEvent.click(screen.getByRole("button", { name: "Valider" }));
    expect(await screen.findByText(/Essais restants : 4/)).toBeVisible();
  });
});

describe("WalletScreen", () => {
  it("shows the money and asks for a payout", async () => {
    signIn();
    const fetchMock = mockApi([
      {
        path: "/me/wallet",
        body: {
          wallets: [
            {
              currency: "XOF",
              pending_minor: 5_000,
              available_minor: 11_000,
              in_progress_minor: 0,
              paid_out_minor: 0,
              minimum_minor: 5_000,
              payout_method: "MTN •••• 3456",
            },
          ],
          payouts: [],
        },
      },
      { path: "/me/wallet/history", body: [] },
      { path: "/me/tax-profile", status: 404, body: {} },
      {
        method: "POST",
        path: "/me/payouts",
        status: 201,
        body: {
          id: "po1",
          amount_minor: 11_000,
          currency: "XOF",
          status: "requested",
          destination: "MTN •••• 3456",
          created_at: "2026-10-13T10:00:00Z",
          paid_at: null,
        },
      },
    ]);
    renderWithProviders(<WalletScreen />);
    expect(await screen.findByRole("heading", { name: "Mon portefeuille" })).toBeVisible();
    expect(screen.getByText("En attente")).toBeVisible();
    expect(screen.getByText("Versement vers : MTN •••• 3456")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /Retirer 11\s?000/ }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/payouts")).toEqual({ amount_minor: 11_000, currency: "XOF" }),
    );
  });
});
