import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { readFilters, toQuery } from "@/components/features/pros/explore/filters";
import { formatDistance, weekdayIn, weekdayName } from "@/lib/pros/format";
import { jsonLdScript, localBusinessJsonLd } from "@/lib/pros/json-ld";
import { ME, mockApi, sentBody } from "@/test/fetch-mock";
import { CARD, myPro, SERVICE, SHOWCASE } from "@/test/pros-fixtures";
import { renderWithProviders } from "@/test/render";

import { HoursSection } from "./my/hours-section";
import { MyShowcase } from "./my/my-showcase";
import { ServicesSection } from "./my/services-section";
import { ProCard } from "./pro-card";
import { ShowcaseView } from "./showcase/showcase-view";

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

describe("format helpers", () => {
  it("names days, distances and today in the pro's time zone", () => {
    expect(weekdayName(0, "fr")).toBe("Lundi");
    expect(weekdayName(6, "en")).toBe("Sunday");
    expect(formatDistance(430, "fr")).toMatch(/^450\sm$/); // narrow no-break space
    expect(formatDistance(2600, "fr")).toMatch(/^2,6\skm$/);
    // 22:30 UTC on Sunday: already Monday in Paris (UTC+2), still Sunday in Cotonou (UTC+1).
    const moment = new Date("2026-10-11T22:30:00Z");
    expect(weekdayIn("Europe/Paris", moment)).toBe(0);
    expect(weekdayIn("Africa/Porto-Novo", moment)).toBe(6);
  });
});

describe("explore filters in the address", () => {
  it("round-trips", () => {
    const filters = readFilters(new URLSearchParams("trade=braids&open=1&price=5000&view=map"));
    expect(filters).toMatchObject({ trade: "braids", openNow: true, priceMax: 5000, view: "map" });
    expect(toQuery(filters)).toEqual({
      trade: "braids",
      open: "1",
      price: "5000",
      currency: "XOF",
      view: "map",
    });
  });
});

describe("LocalBusiness structured data", () => {
  it("describes the salon, its hours and prices", () => {
    const data = localBusinessJsonLd(SHOWCASE, "https://solangeglow.com/fr/aicha") as Record<
      string,
      unknown
    >;
    expect(data["@type"]).toBe("HairSalon");
    expect(data.geo).toEqual({ "@type": "GeoCoordinates", latitude: 6.3552, longitude: 2.3601 });
    expect(JSON.stringify(data)).toContain('"price":"15000"');
    expect(data.sameAs).toEqual(["https://www.instagram.com/aicha"]);
  });

  it("never gives the address of a pro who only goes to her clients", () => {
    const homeOnly = { ...SHOWCASE, place: { ...SHOWCASE.place, receives_clients: false } };
    const text = JSON.stringify(localBusinessJsonLd(homeOnly, "https://x"));
    expect(text).not.toContain("Rue 12");
    expect(text).not.toContain("GeoCoordinates");
  });

  it("cannot close the script tag", () => {
    expect(jsonLdScript({ name: "</script><b>" })).not.toContain("</script>");
  });
});

describe("ProCard", () => {
  it("shows who, where, open, rating and the lowest price", () => {
    renderWithProviders(<ProCard pro={CARD} />);
    const card = screen.getByRole("link", { name: /Aïcha Tresses/ });
    expect(card).toHaveAttribute("href", "/fr/aicha");
    expect(within(card).getByText(/2,6 km, Fidjrossè, Cotonou/)).toBeInTheDocument();
    expect(within(card).getByText("Ouvert")).toBeInTheDocument();
    expect(within(card).getByText("À domicile")).toBeInTheDocument();
    expect(within(card).getByText(/3\s000 FCFA/)).toBeInTheDocument();
  });
});

describe("ShowcaseView", () => {
  it("shows services with options, hours and how to find her", () => {
    mockApi([]);
    renderWithProviders(<ShowcaseView showcase={SHOWCASE} />);
    expect(screen.getByRole("heading", { level: 1, name: "Aïcha Tresses" })).toBeInTheDocument();
    expect(screen.getByText("Pro vérifiée")).toBeInTheDocument();
    expect(screen.getByText("Knotless mi-dos")).toBeInTheDocument();
    expect(screen.getByText("En option : Mèches fournies")).toBeInTheDocument();
    expect(screen.getByText("Après la pharmacie, portail bleu.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Itinéraire/ })).toHaveAttribute(
      "href",
      SHOWCASE.place.directions_url,
    );
    expect(screen.getByRole("button", { name: /Je suis devant/ })).toBeInTheDocument();
  });

  it("keeps the address of a home-visit pro private", () => {
    const homeOnly = {
      ...SHOWCASE,
      place: { ...SHOWCASE.place, receives_clients: false, address: null, landmarks: "" },
      travel: { ...SHOWCASE.travel, travels_to_clients: true, radius_km: 12, fee_minor: 2000 },
    };
    renderWithProviders(<ShowcaseView showcase={homeOnly} />);
    expect(screen.getByText(/se déplace chez toi\. Son adresse reste privée/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Je suis devant/ })).not.toBeInTheDocument();
    expect(screen.getByText("Se déplace à domicile jusqu'à 12 km")).toBeInTheDocument();
  });

  it("tells the pro when the client is at the door", async () => {
    const fetchMock = mockApi([
      { method: "POST", path: "/pros/aicha/arrival", body: { sent: true } },
    ]);
    renderWithProviders(<ShowcaseView showcase={SHOWCASE} />);
    await userEvent.click(screen.getByRole("button", { name: /Je suis devant/ }));
    expect(await screen.findByText("Aïcha Tresses sait que tu es devant.")).toBeInTheDocument();
    expect(fetchMock.records.some((r) => r.path === "/api/v1/pros/aicha/arrival")).toBe(true);
  });
});

describe("Ma vitrine", () => {
  it("lists what is missing and publishes when ready", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: { ...ME, roles: ["client", "pro"], onboarding_required: false } },
      { path: "/me/pro", body: myPro({ missing: ["location", "services"] }) },
    ]);
    const { unmount } = renderWithProviders(<MyShowcase />);
    expect(await screen.findByText("Pour publier, il manque :")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Au moins une prestation/ })).toHaveAttribute(
      "href",
      "/fr/pro/services",
    );
    expect(screen.getByRole("button", { name: /Publier ma vitrine/ })).toBeDisabled();
    unmount();

    mockApi([
      { path: "/me", body: { ...ME, roles: ["client", "pro"], onboarding_required: false } },
      { path: "/me/pro", body: myPro() },
      { method: "POST", path: "/me/pro/publication", body: myPro({ status: "published" }) },
    ]);
    renderWithProviders(<MyShowcase />);
    await userEvent.click(await screen.findByRole("button", { name: /Publier ma vitrine/ }));
    expect(await screen.findByText("Publié ! Ta vitrine est en ligne.")).toBeInTheDocument();
    expect(fetchMock).toBeDefined();
  });

  it("adds a service with a waiting time and an option", async () => {
    const fetchMock = mockApi([
      { method: "POST", path: "/me/pro/services", status: 201, body: SERVICE },
      { path: "/me/pro", body: myPro() },
    ]);
    renderWithProviders(<ServicesSection pro={myPro({ services: [] })} />);
    await userEvent.click(screen.getByRole("button", { name: /Ajouter une prestation/ }));
    await userEvent.type(screen.getByLabelText("Nom"), "Coloration");
    await userEvent.click(screen.getByRole("button", { name: "À partir de" }));
    await userEvent.type(screen.getByLabelText("Montant (FCFA)"), "12 000");
    await userEvent.selectOptions(screen.getByLabelText("Temps de travail"), "30");
    await userEvent.selectOptions(screen.getByLabelText("Temps de pose"), "40");
    await userEvent.selectOptions(screen.getByLabelText("Travail après la pose"), "20");
    await userEvent.click(screen.getByRole("button", { name: /Ajouter une option/ }));
    await userEvent.type(screen.getByLabelText("Option"), "Soin");
    await userEvent.type(screen.getByLabelText("Supplément"), "2000");
    await userEvent.click(screen.getByRole("button", { name: "Enregistrer la prestation" }));

    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/pro/services")).toMatchObject({
        name: "Coloration",
        price_kind: "from",
        price_minor: 12000,
        steps: [
          { kind: "work", duration_minutes: 30 },
          { kind: "wait", duration_minutes: 40 },
          { kind: "work", duration_minutes: 20 },
        ],
        options: [{ name: "Soin", price_minor: 2000 }],
      }),
    );
  });

  it("saves a day with a lunch break", async () => {
    const fetchMock = mockApi([
      { method: "PUT", path: "/me/pro/hours", body: { periods: [], closures: [] } },
      { path: "/me/pro", body: myPro() },
    ]);
    renderWithProviders(<HoursSection pro={myPro({ hours: [] })} />);
    const monday = screen.getByText("Lundi").closest("li")!;
    await userEvent.click(within(monday).getByRole("button", { name: "Fermé" }));
    await userEvent.click(within(monday).getByRole("button", { name: /Ajouter une pause/ }));
    await userEvent.click(screen.getByRole("button", { name: /Enregistrer les horaires/ }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/me/pro/hours")).toEqual({
        periods: [
          { weekday: 0, opens_at: "09:00", closes_at: "12:00" },
          { weekday: 0, opens_at: "14:00", closes_at: "18:00" },
        ],
      }),
    );
  });
});
