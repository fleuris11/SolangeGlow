import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { PickupPoint, SelectionProduct } from "@/lib/api/selection";
import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { SpecialRequests } from "./requests";
import { SelectionBuy } from "./selection-buy";

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

const ESTIMATE = { from: "2026-11-02", to: "2026-11-06" };

const PRODUCT: SelectionProduct = {
  id: "s1",
  slug: "fond-de-teint-fenty",
  title: "Fond de teint Fenty",
  merchant_name: "Sephora",
  aisle: "trending",
  price_xof: 25300,
  available: true,
  photo: null,
  group: null,
  description: "",
  category: { key: "makeup", name: "Maquillage", air_restricted: false },
  express_price_xof: 29100,
  options: ["330", "385"],
  photos: [],
  estimates: { grouped: ESTIMATE, express: ESTIMATE, group: null },
};

const POINTS: PickupPoint[] = [
  {
    id: "pt1",
    name: "Solange Glow Haie Vive",
    city: "Cotonou",
    address: "Haie Vive",
    landmarks: "",
    hours: "",
  },
];

const amount = (element: HTMLElement) => element.textContent?.replace(/\s/g, " ");

describe("SelectionBuy", () => {
  it("shows the final price of each way and pays the express one", async () => {
    signIn();
    const fetchMock = mockApi([
      { method: "POST", path: "/selection/orders", status: 201, body: { id: "o1", payment: null } },
    ]);
    renderWithProviders(<SelectionBuy product={PRODUCT} points={POINTS} icons={{ lock: null }} />);
    const pay = screen.getByRole("button", { name: /Payer/ });
    expect(amount(pay)).toBe("Payer 25 300 FCFA");
    await userEvent.click(screen.getByRole("button", { name: "385" }));
    await userEvent.click(screen.getByText("Express"));
    await userEvent.click(screen.getByRole("button", { name: "Un de plus" }));
    expect(amount(pay)).toBe("Payer 58 200 FCFA");
    await userEvent.click(pay);
    await waitFor(() =>
      expect(sentBody(fetchMock, "/selection/orders")).toEqual({
        product_id: "s1",
        shipping_mode: "express",
        pickup_point_id: "pt1",
        option: "385",
        quantity: 2,
        group: false,
      }),
    );
  });

  it("offers the group pre-order with its progress", () => {
    renderWithProviders(
      <SelectionBuy
        product={{
          ...PRODUCT,
          group: {
            id: "g1",
            price_xof: 21000,
            target: 20,
            count: 7,
            ends_at: "2026-11-01T12:00:00Z",
          },
          estimates: { ...PRODUCT.estimates, group: ESTIMATE },
        }}
        points={POINTS}
        icons={{ lock: null }}
      />,
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "7");
    expect(amount(screen.getByRole("button", { name: /Payer/ }))).toBe("Payer 21 000 FCFA");
  });
});

describe("SpecialRequests", () => {
  it("sends a link and lists the requests", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/selection/requests", body: [] },
      { method: "POST", path: "/selection/requests", status: 201, body: {} },
    ]);
    renderWithProviders(<SpecialRequests />);
    expect(await screen.findByText("Pas encore de demande.")).toBeVisible();
    await userEvent.type(screen.getByLabelText("Lien du produit"), "https://www.zara.com/robe");
    await userEvent.click(screen.getByRole("button", { name: "Envoyer ma demande" }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/selection/requests")).toEqual({
        link: "https://www.zara.com/robe",
        note: "",
        photo: null,
      }),
    );
  });
});
