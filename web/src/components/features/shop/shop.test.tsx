import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Cart, ProductDetail } from "@/lib/api/shop";
import { moneyInput, parseMoney } from "@/lib/money";
import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { ProductBuy } from "./buy-buttons";
import { CartScreen } from "./cart";

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

const DELIVERY = {
  is_open: true,
  pickup: true,
  pickup_note: "",
  seller_delivery: false,
  partner_delivery: false,
  partner_name: "",
  return_policy: "",
  zones: [],
};

const SHOP = {
  slug: "gloria",
  name: "Gloria Make-up",
  photo: null,
  city: "Cotonou",
  is_verified: true,
  rating_average: null,
  rating_count: 0,
};

const variant = (id: string, shade: string, stock: number) => ({
  id,
  shade,
  swatch: "#A0522D",
  size: "",
  color: "",
  label: shade,
  price_minor: 8000,
  before_minor: null,
  own_price_minor: null,
  stock,
  is_active: true,
});

const PRODUCT: ProductDetail = {
  id: "p1",
  slug: "fond-de-teint",
  title: "Fond de teint Velours",
  category: { key: "makeup", name: "Maquillage", icon: "" },
  currency: "XOF",
  price_minor: 8000,
  before_minor: null,
  photo: null,
  in_stock: true,
  flash_sale: null,
  sold_count: 0,
  wished: false,
  shop_slug: "gloria",
  description: "Fini mat.",
  description_voice: null,
  video: null,
  photos: [],
  variants: [variant("v1", "Caramel", 3), variant("v2", "Ébène", 0)],
  prep_days: 1,
  next_flash_sale: null,
  shop: SHOP,
  delivery: DELIVERY,
  watching: [],
  is_mine: false,
  link: "/gloria/shop/fond-de-teint",
};

const ICONS = { cart: null, heart: null, heartFilled: null, bell: null, flash: null };

describe("prices typed by a pro", () => {
  it("reads FCFA and euros in the smallest unit", () => {
    expect(parseMoney("8 000", "XOF")).toBe(8000);
    expect(parseMoney("12,50", "EUR")).toBe(1250);
    expect(parseMoney("douze", "EUR")).toBeNull();
    expect(moneyInput(1250, "EUR", "fr")).toBe("12,50");
    expect(moneyInput(8000, "XOF", "fr")).toBe("8000");
  });
});

describe("ProductBuy", () => {
  it("adds the chosen shade and quantity to the cart", async () => {
    signIn();
    const fetchMock = mockApi([
      { method: "POST", path: "/shop/cart/items", status: 201, body: {} },
    ]);
    renderWithProviders(<ProductBuy product={PRODUCT} locale="fr" icons={ICONS} />);
    await userEvent.click(screen.getByRole("button", { name: "Un de plus" }));
    expect(screen.getByText("Plus que 3")).toBeVisible();
    const add = screen.getByRole("button", { name: /Ajouter au panier/ });
    expect(add.textContent?.replace(/\s/g, " ")).toBe("Ajouter au panier, 16 000 FCFA");
    await userEvent.click(add);
    await waitFor(() =>
      expect(sentBody(fetchMock, "/shop/cart/items")).toEqual({ variant_id: "v1", quantity: 2 }),
    );
    expect(await screen.findByRole("link", { name: "Voir mon panier" })).toBeVisible();
  });

  it("offers an alert when the shade is sold out", async () => {
    signIn();
    const fetchMock = mockApi([{ method: "PUT", path: "/shop/alerts/v2", status: 204 }]);
    renderWithProviders(<ProductBuy product={PRODUCT} locale="fr" icons={ICONS} />);
    await userEvent.click(screen.getByRole("button", { name: /Ébène/ }));
    await userEvent.click(screen.getByRole("button", { name: "Préviens-moi quand il revient" }));
    await waitFor(() =>
      expect(fetchMock.records.some((r) => r.path === "/api/v1/shop/alerts/v2")).toBe(true),
    );
    expect(await screen.findByRole("button", { name: "Ne plus me prévenir" })).toBeVisible();
  });
});

describe("CartScreen", () => {
  it("shows each shop and opens the checkout", async () => {
    signIn();
    const cart: Cart = {
      count: 1,
      shops: [
        {
          shop: SHOP,
          pro_id: "pro1",
          currency: "XOF",
          delivery: DELIVERY,
          subtotal_minor: 16000,
          prep_days: 1,
          lines: [
            {
              id: "l1",
              kind: "variant",
              product_id: "p1",
              product_slug: "fond-de-teint",
              variant_id: "v1",
              bundle_id: null,
              title: "Fond de teint Velours",
              variant_label: "Caramel",
              photo: null,
              unit_price_minor: 8000,
              before_minor: null,
              quantity: 2,
              total_minor: 16000,
              stock_left: 3,
              available: true,
              flash_ends_at: null,
            },
          ],
        },
      ],
    };
    mockApi([{ path: "/shop/cart", body: cart }]);
    renderWithProviders(<CartScreen />);
    expect(await screen.findByRole("heading", { name: "Gloria Make-up" })).toBeVisible();
    expect(screen.getByText("Caramel")).toBeVisible();
    const order = screen.getByRole("link", { name: /Commander/ });
    expect(order.textContent?.replace(/\s/g, " ")).toBe("Commander, 16 000 FCFA");
    expect(order).toHaveAttribute("href", "/fr/checkout");
  });

  it("invites to explore when it is empty", async () => {
    signIn();
    mockApi([{ path: "/shop/cart", body: { count: 0, shops: [] } }]);
    renderWithProviders(<CartScreen />);
    expect(await screen.findByText("Ton panier est vide")).toBeVisible();
  });
});
