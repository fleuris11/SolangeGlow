import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { LiveState, MySaleLives } from "@/lib/api/live";
import { called, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { CallLine } from "../messaging/call-line";
import { BuySheet } from "./buy-sheet";
import { LiveRoom } from "./live-room";
import { MySaleLivesTab } from "./my-sale-lives";

const LIVE = "8f3c2a8e-0000-4000-8000-0000000000aa";

function state(overrides: Partial<LiveState> = {}): LiveState {
  const later = new Date(Date.now() + 3 * 3600_000).toISOString();
  return {
    kind: "training",
    source_id: LIVE,
    title: "Maquillage mariée : vos questions",
    status: "scheduled",
    starts_at: later,
    ends_at: later,
    time_zone: "Africa/Porto-Novo",
    can_start_at: later,
    started_at: null,
    ends_by: null,
    host: { name: "Institut Prisca", slug: "institut-prisca", photo: null },
    is_host: false,
    can_watch: true,
    can_ask: false,
    can_raise_hand: true,
    signed_in: true,
    viewers: 0,
    max_viewers: 300,
    speaking: false,
    my_hand: null,
    hands: [],
    questions: [],
    replay: null,
    link: `/academie/live/${LIVE}`,
    cover_url: "",
    sale: null,
    ...overrides,
  };
}

describe("CallLine", () => {
  it("says the kind and length of a call, or that it was missed", () => {
    const call = { id: "c", kind: "video" as const, caller_id: "u1", duration_seconds: 185 };
    const cases = [
      { status: "ended" as const, mine: true, text: "Appel vidéo, 3 min" },
      { status: "missed" as const, mine: false, text: "Appel manqué" },
      { status: "missed" as const, mine: true, text: "Pas de réponse" },
    ];
    for (const { status, mine, text } of cases) {
      const view = renderWithProviders(
        <CallLine call={{ ...call, status }} mine={mine} time="10:00" />,
      );
      expect(screen.getByText(text)).toBeInTheDocument();
      view.unmount();
    }
  });
});

describe("LiveRoom", () => {
  it("shows the waiting screen; the host goes on air only in her window", async () => {
    mockApi([{ path: `/live/training/${LIVE}`, body: state({ is_host: true }) }]);
    renderWithProviders(<LiveRoom kind="training" id={LIVE} />);
    expect(await screen.findByText(/Commence dans/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Passer en direct/ })).toBeDisabled();
    expect(screen.getByText(/Tu pourras passer en direct à partir de/)).toBeInTheDocument();
  });

  it("offers the replay and the questions once it is over", async () => {
    mockApi([
      {
        path: `/live/training/${LIVE}`,
        body: state({
          status: "ended",
          replay: {
            status: "ready",
            until: null,
            urls: { low: "/s3/low.mp4", medium: "/s3/medium.mp4" },
            duration: 1800,
          },
          questions: [
            {
              id: "q1",
              name: "Awa",
              text: "Quel fond de teint ?",
              at_second: 125,
              answered: true,
              mine: false,
              held: false,
              created_at: new Date().toISOString(),
            },
          ],
        }),
      },
    ]);
    renderWithProviders(<LiveRoom kind="training" id={LIVE} />);
    expect(await screen.findByLabelText(/Replay de/)).toBeInTheDocument();
    expect(screen.getByText("Quel fond de teint ?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "à 2:05" })).toBeInTheDocument();
  });
});

describe("BuySheet", () => {
  it("adds the chosen shade to the cart with the live, then opens the payment", async () => {
    const product = "8f3c2a8e-0000-4000-8000-0000000000bb";
    const fetchMock = mockApi([
      {
        path: `/shop/products/${product}`,
        body: {
          id: product,
          variants: [
            { id: "v1", label: "Mangue", price_minor: 4000, stock: 3, is_active: true },
            { id: "v2", label: "Cerise", price_minor: 4000, stock: 0, is_active: true },
          ],
        },
      },
      { method: "POST", path: "/shop/cart/items", status: 201, body: { shops: [] } },
    ]);
    const pin = {
      product_id: product,
      slug: "gloss",
      name: "Gloss",
      price_minor: 4000,
      currency: "XOF",
      photo: null,
      in_stock: true,
      pinned: true,
    };
    renderWithProviders(
      <BuySheet
        pin={pin}
        liveId={LIVE}
        signedIn
        onClose={() => undefined}
        onSignIn={() => undefined}
      />,
    );
    expect(await screen.findByRole("button", { name: "Cerise" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Mangue" }));
    await userEvent.click(screen.getByRole("button", { name: /Ajouter au panier/ }));
    expect(await screen.findByText("C'est dans ton panier")).toBeInTheDocument();
    expect(sentBody(fetchMock, "/shop/cart/items")).toEqual({
      variant_id: "v1",
      quantity: 1,
      sale_live_id: LIVE,
    });
    expect(screen.getByRole("link", { name: /Payer mon panier/ })).toHaveAttribute(
      "target",
      "_blank",
    );
  });
});

describe("MySaleLivesTab", () => {
  it("tells when the lives of the month are used", async () => {
    const lives: MySaleLives = {
      results: [],
      quota: { used: 2, allowed: 2 },
      open: true,
      can_sell: true,
    };
    const fetchMock = mockApi([{ path: "/me/shop/lives", body: lives }]);
    renderWithProviders(<MySaleLivesTab />);
    expect(await screen.findByText(/Tu as utilisé tes lives du mois/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Programmer le live/ })).toBeDisabled();
    await waitFor(() => expect(called(fetchMock, "/me/shop/lives")).toBe(true));
  });
});
