import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GiftQuote, GiftReception as Reception } from "@/lib/api/gifts";
import { called, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { GlowCardPay } from "./glow-card-pay";
import { OfferFlow } from "./offer-flow";
import { GiftReception } from "./reception";

const TOKEN = "secret-token";
const eur = (amount_minor: number) => ({ amount_minor, currency: "EUR" });
const xof = (amount_minor: number) => ({ amount_minor, currency: "XOF" });

const QUOTE: GiftQuote = {
  kind: "card",
  title: "Carte cadeau Glow",
  value: xof(19_678),
  price: eur(3_000),
  fee: eur(180),
  total: eur(3_180),
  rate: "655.957",
  card_min: eur(1_000),
  card_max: eur(50_000),
  validity_days: 365,
  cancel_days: 14,
  message_max_seconds: 60,
  photo: null,
  pro: null,
};

function gift(overrides: Partial<Reception> = {}): Reception {
  return {
    status: "sent",
    kind: "card",
    locked: false,
    opens_at: new Date().toISOString(),
    is_giver: false,
    from_name: "Grâce",
    recipient_name: "Awa",
    occasion: "birthday",
    message: "Joyeux anniversaire !",
    message_media: null,
    title: "Carte cadeau Glow",
    value: xof(19_678),
    balance: xof(19_678),
    expires_on: "2027-10-28",
    expired: false,
    cancelled: false,
    usable: true,
    unused: true,
    code: "ABCD234567",
    claimed: false,
    pro: null,
    service_id: null,
    thing: { name: "Carte cadeau Glow", photo: null, available: true },
    uses: [],
    pickup_points: [],
    recipient_phone: "+2290197000201",
    time_zone: "Africa/Porto-Novo",
    photos: [],
    proof_status: "",
    proof_sent_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  document.cookie = "sg_signed_in=1; path=/";
});

describe("OfferFlow", () => {
  it("offers a Glow gift card in 4 steps and opens the payment", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi([
      {
        path: "/gifts/ideas",
        body: { products: [], selection: [], card_min: eur(1_000), card_max: eur(50_000) },
      },
      { path: "/gifts/quote", body: QUOTE },
      {
        method: "POST",
        path: "/gifts",
        status: 201,
        body: { gift: {}, checkout_url: "/fr/pay/test/p1" },
      },
    ]);
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    renderWithProviders(<OfferFlow start={{ kind: "card" }} />);
    await user.click(await screen.findByRole("button", { name: /^30,00/ }));
    expect(await screen.findByText(/Valeur 19 678 FCFA/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuer" }));
    await user.type(screen.getByLabelText("Son prénom"), "Awa");
    await user.type(screen.getByLabelText("Son numéro au Bénin"), "+2290197000201");
    await user.click(screen.getByRole("button", { name: "Anniversaire" }));
    await user.click(screen.getByRole("button", { name: "Continuer" }));
    await user.type(screen.getByLabelText("Ton message"), "Fais-toi plaisir");
    await user.click(screen.getByRole("button", { name: "Continuer" }));
    expect(screen.getByText(/^31,80/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Payer 31,80/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/fr/pay/test/p1"));
    expect(sentBody(fetchMock, "/gifts")).toMatchObject({
      kind: "card",
      amount_minor: 3_000,
      recipient_name: "Awa",
      occasion: "birthday",
      message: "Fais-toi plaisir",
      send_at: null,
    });
    vi.unstubAllGlobals();
  });
});

describe("GiftReception", () => {
  it("waits for its day, without showing the gift", async () => {
    mockApi([
      {
        path: `/gifts/open/${TOKEN}`,
        body: { ...gift({ locked: true, opens_at: "2030-05-26T07:00:00Z" }) },
      },
    ]);
    renderWithProviders(<GiftReception token={TOKEN} />);
    expect(await screen.findByText(/Il s'ouvre le 26 mai/)).toBeInTheDocument();
  });

  it("opens the envelope, then shows the message and the card code", async () => {
    const user = userEvent.setup();
    mockApi([{ path: `/gifts/open/${TOKEN}`, body: gift() }]);
    renderWithProviders(<GiftReception token={TOKEN} />);
    expect(await screen.findByText("Awa, un cadeau pour toi")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ouvrir mon cadeau" }));
    expect(screen.getByRole("img", { name: "Cadeau ouvert" })).toBeInTheDocument();
    expect(screen.getByText(/Joyeux anniversaire !/)).toBeInTheDocument();
    expect(screen.getByText("ABCD234567")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Garder dans mon compte" })).toBeInTheDocument();
  });

  it("books the offered service at a free time, already paid", async () => {
    const user = userEvent.setup();
    const start = "2030-01-07T09:00:00Z";
    const fetchMock = mockApi([
      {
        path: `/gifts/open/${TOKEN}`,
        body: gift({
          kind: "service",
          code: null,
          pro: { slug: "aicha", name: "Aïcha Tresses", photo: null, city: "Cotonou" },
          service_id: "s1",
          thing: { name: "Tresses", photo: null, available: true, duration_minutes: 120 },
        }),
      },
      {
        path: "/pros/aicha/booking/slots",
        body: {
          days: [
            {
              day: "2030-01-07",
              slots: [{ start, end: start, staff_id: null, discount_percent: 0 }],
            },
          ],
          next_day: null,
        },
      },
      {
        method: "POST",
        path: `/gifts/open/${TOKEN}/book`,
        status: 201,
        body: { appointment: { id: "a1" }, manage_url: "/rdv/xyz", checkout_url: null },
      },
    ]);
    renderWithProviders(<GiftReception token={TOKEN} />);
    await user.click(await screen.findByRole("button", { name: "Ouvrir mon cadeau" }));
    await user.click(await screen.findByRole("button", { name: /^10/ }));
    await user.click(screen.getByRole("button", { name: /Réserver lundi 7 janvier à 10/ }));
    expect(await screen.findByRole("link", { name: /Voir mon rendez-vous/ })).toHaveAttribute(
      "href",
      "/fr/rdv/xyz",
    );
    expect(sentBody(fetchMock, `/gifts/open/${TOKEN}/book`)).toMatchObject({ start });
  });

  it("sends a photo to the giver only after her yes", async () => {
    const user = userEvent.setup();
    const used = gift({
      kind: "service",
      unused: false,
      uses: [
        {
          id: "u1",
          label: "Tresses chez Aïcha",
          kind: "booking",
          amount: xof(15_000),
          refunded: xof(0),
          payment_status: "released",
          created_at: "2030-01-06T10:00:00Z",
          starts_at: "2030-01-07T09:00:00Z",
          status: "completed",
          link: "/rdv/xyz",
          receipt_code: null,
          pickup_point: "",
        },
      ],
      photos: [
        {
          id: "m1",
          source: "pro",
          media: {
            id: "m1",
            kind: "image",
            status: "ready",
            error: null,
            blurhash: null,
            width: 10,
            height: 10,
            duration: null,
            urls: { medium: "/s3/m1.webp" },
          },
        },
      ],
    });
    const fetchMock = mockApi([
      { path: `/gifts/open/${TOKEN}`, body: used },
      {
        method: "POST",
        path: `/gifts/open/${TOKEN}/proof`,
        body: { ...used, proof_status: "sent" },
      },
    ]);
    renderWithProviders(<GiftReception token={TOKEN} />);
    expect(await screen.findByText("Envoyer une photo à Grâce ?")).toBeInTheDocument();
    expect(screen.getByText("Terminé")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Oui, envoyer" }));
    expect(await screen.findByText("Ta photo est partie chez Grâce.")).toBeInTheDocument();
    expect(sentBody(fetchMock, `/gifts/open/${TOKEN}/proof`)).toEqual({
      media_id: "m1",
      send: true,
    });
  });
});

describe("GlowCardPay", () => {
  it("shows the balance, then pays the whole purchase", async () => {
    const user = userEvent.setup();
    const onPaid = vi.fn();
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/gifts/cards/check",
        body: { balance: xof(19_678), expires_on: "2027-10-28", from_name: "Grâce" },
      },
      { method: "POST", path: "/gifts/cards/pay", body: { balance: xof(10_408) } },
    ]);
    renderWithProviders(<GlowCardPay target={{ groupId: "g1" }} onPaid={onPaid} />);
    await user.click(screen.getByRole("button", { name: "J'ai une carte cadeau Glow" }));
    await user.type(screen.getByLabelText("Code de la carte"), "ABCD234567");
    await user.click(screen.getByRole("button", { name: "Voir le solde" }));
    expect(await screen.findByText("Il reste 19 678 FCFA sur la carte.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Payer avec ma carte" }));
    await waitFor(() => expect(onPaid).toHaveBeenCalledWith({ groupId: "g1" }));
    expect(sentBody(fetchMock, "/gifts/cards/pay")).toEqual({ code: "ABCD234567", group_id: "g1" });
    expect(called(fetchMock, "/gifts/cards/check", "POST")).toBe(true);
  });
});
