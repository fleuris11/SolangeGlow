import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Ad } from "@/lib/api/ads";
import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { AdSlot, SponsoredPro } from "./ad-cards";
import { BoostScreen } from "./boost-screen";
import { SplashAd } from "./splash";

const AD: Ad = {
  id: "a1",
  placement: "home_banner",
  format: "image",
  sponsor: "Karité Doux",
  house: false,
  title: "Le karité qui nourrit",
  text: "-10 % ce mois-ci.",
  cta: "Voir la boutique",
  click_url: "/api/v1/ads/click/abc",
  media: [],
  pro: null,
  product: null,
};

beforeEach(() => {
  document.cookie = "sg_signed_in=1; path=/";
});

describe("ads", () => {
  it("always says « Sponsored » and leads through the click link", () => {
    renderWithProviders(
      <AdSlot list={{ results: [AD], adsense: null, feed_every: 6, splash_seconds: 5 }} />,
    );
    expect(screen.getByText("Sponsorisé par Karité Doux")).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: "Voir la boutique" });
    expect(cta).toHaveAttribute("href", "/api/v1/ads/click/abc");
    expect(cta).toHaveAttribute("rel", "sponsored");
  });

  it("shows a house promotion as such and nothing when there is no ad", () => {
    const empty = renderWithProviders(
      <AdSlot list={{ results: [], adsense: null, feed_every: 6, splash_seconds: 5 }} />,
    );
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    empty.unmount();
    renderWithProviders(
      <AdSlot
        list={{
          results: [{ ...AD, house: true }],
          adsense: null,
          feed_every: 6,
          splash_seconds: 5,
        }}
      />,
    );
    expect(screen.getByText("Promo Solange Glow")).toBeInTheDocument();
  });

  it("shows a boosted pro first, marked « Sponsored »", () => {
    renderWithProviders(
      <SponsoredPro
        ad={{
          ...AD,
          placement: "search",
          format: "native",
          sponsor: "Aïcha Tresses",
          pro: {
            slug: "aicha",
            name: "Aïcha Tresses",
            photo: null,
            city: "Cotonou",
            trades: [{ key: "braids", name: "Tresses" }],
            rating_average: 4.8,
            rating_count: 12,
            verified: true,
          },
        }}
      />,
    );
    expect(screen.getByRole("link", { name: "Sponsorisé : Aïcha Tresses" })).toBeInTheDocument();
    expect(screen.getByText("Sponsorisé par Aïcha Tresses")).toBeInTheDocument();
    expect(screen.getByText("Tresses — Cotonou")).toBeInTheDocument();
  });
});

describe("BoostScreen", () => {
  it("chooses a week and opens the payment page", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    const fetchMock = mockApi([
      {
        path: "/ads/boosts",
        body: {
          open: true,
          prices: { currency: "XOF", day: 1000, week: 5000 },
          running_until: null,
          boosts: [],
        },
      },
      { method: "POST", path: "/ads/boosts", body: { checkout_url: "/fr/pay/test/p1" } },
    ]);
    renderWithProviders(<BoostScreen justPaid={false} />);
    expect(await screen.findByRole("heading", { name: "Booster ma vitrine" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /1 semaine/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await user.click(screen.getByRole("radio", { name: /1 jour/ }));
    await user.click(screen.getByRole("button", { name: /Payer 1.000.FCFA/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/fr/pay/test/p1"));
    expect(sentBody(fetchMock, "/ads/boosts")).toEqual({ duration: "day" });
    vi.unstubAllGlobals();
  });
});

describe("SplashAd", () => {
  it("can be skipped at once", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mockApi([
      {
        path: "/ads",
        body: {
          results: [{ ...AD, placement: "splash" }],
          adsense: null,
          feed_every: 6,
          splash_seconds: 5,
        },
      },
    ]);
    renderWithProviders(<SplashAd onClose={onClose} />);
    expect(
      await screen.findByRole("dialog", { name: "Le karité qui nourrit" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Sponsorisé par Karité Doux")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Passer/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it("closes by itself when nothing is sold", async () => {
    const onClose = vi.fn();
    mockApi([
      { path: "/ads", body: { results: [], adsense: null, feed_every: 6, splash_seconds: 5 } },
    ]);
    renderWithProviders(<SplashAd onClose={onClose} />);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});
