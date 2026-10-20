import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import type { Appointment, BookingPage } from "@/lib/api/booking";
import { blocksFor, gridRange, snapMinutes, type Column } from "@/lib/booking/agenda-layout";
import {
  addDays,
  durationLabel,
  localDay,
  mondayOf,
  timeAt,
  weekdayOf,
  zonedToIso,
} from "@/lib/booking/time";
import { mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { AppointmentView } from "./appointment-view";
import { BookingFlow } from "./booking-flow";

const BENIN = "Africa/Porto-Novo";
/** Times are written with non-breaking spaces (« 10 h 30 » stays on one line). */
const plain = (text: string) => text.replace(/\s/g, " ");
const PARIS = "Europe/Paris";

describe("times at the salon", () => {
  it("turns a local time into the right moment, summer time included", () => {
    expect(zonedToIso("2030-01-07", 630, BENIN)).toBe("2030-01-07T09:30:00.000Z");
    expect(zonedToIso("2030-07-01", 600, PARIS)).toBe("2030-07-01T08:00:00.000Z");
    expect(zonedToIso("2030-10-27", 540, PARIS)).toBe("2030-10-27T08:00:00.000Z"); // back to winter
    expect(localDay("2030-01-07T23:30:00Z", BENIN)).toBe("2030-01-08");
  });

  it("speaks like people do", () => {
    expect(plain(timeAt("2030-01-07T09:30:00Z", BENIN, "fr"))).toBe("10 h 30");
    expect(plain(timeAt("2030-01-07T09:00:00Z", BENIN, "fr"))).toBe("10 h");
    expect(plain(durationLabel(90, "fr"))).toBe("1 h 30");
    expect(durationLabel(45, "fr")).toBe("45 min");
    expect(weekdayOf("2030-01-07")).toBe(0);
    expect(mondayOf("2030-01-12")).toBe("2030-01-07");
    expect(addDays("2030-01-31", 1)).toBe("2030-02-01");
  });
});

const PRO = {
  id: "pro1",
  slug: "salon-estelle",
  name: "Salon Estelle",
  photo: null,
  city: "Cotonou",
  district: "Fidjrossè",
  address: "",
  is_verified: true,
  rating_average: null,
  rating_count: 0,
  timezone: BENIN,
};

function appointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: "a1",
    reference: "RDV-ABC1234",
    status: "confirmed",
    source: "online",
    pro: PRO,
    service_id: "s1",
    service_name: "Coloration",
    option_names: [],
    starts_at: "2030-01-07T09:00:00+00:00",
    ends_at: "2030-01-07T11:00:00+00:00",
    client_id: null,
    client_name: "Inès",
    client_phone: "",
    is_guest: true,
    price_minor: 20000,
    currency: "XOF",
    discount_percent: 0,
    deposit_minor: 0,
    payment: null,
    note: "",
    pro_message: "",
    proposed_from: null,
    answer_due_at: null,
    group_id: null,
    steps: [
      {
        position: 0,
        kind: "work",
        label: "",
        starts_at: "2030-01-07T09:00:00+00:00",
        ends_at: "2030-01-07T09:30:00+00:00",
        staff_id: "st1",
        staff_name: "Estelle",
        resource_id: null,
      },
      {
        position: 1,
        kind: "wait",
        label: "Pose",
        starts_at: "2030-01-07T09:30:00+00:00",
        ends_at: "2030-01-07T10:30:00+00:00",
        staff_id: null,
        staff_name: "",
        resource_id: null,
      },
      {
        position: 2,
        kind: "work",
        label: "",
        starts_at: "2030-01-07T10:30:00+00:00",
        ends_at: "2030-01-07T11:00:00+00:00",
        staff_id: "st2",
        staff_name: "Carine",
        resource_id: null,
      },
    ],
    free_cancel_until: "2030-01-06T09:00:00+00:00",
    late_cancel: false,
    can_cancel: true,
    can_review: false,
    advice: [],
    photos: [],
    created_at: "2030-01-01T09:00:00+00:00",
    ...overrides,
  };
}

describe("agenda layout", () => {
  it("draws the waiting time with the person before and the last step elsewhere", () => {
    const columns: Column[] = [
      { key: "st1", day: "2030-01-07", staffId: "st1" },
      { key: "st2", day: "2030-01-07", staffId: "st2" },
    ];
    const blocks = blocksFor([appointment()], columns, BENIN);
    const first = blocks.find((b) => b.column === "st1")!;
    const second = blocks.find((b) => b.column === "st2")!;
    expect([first.start, first.end]).toEqual([600, 690]); // 10:00 to 11:30 in Cotonou
    expect(first.segments.map((s) => s.waiting)).toEqual([false, true]);
    expect([second.start, second.end]).toEqual([690, 720]);
    expect(snapMinutes(70, 1.6, 15)).toBe(45);
  });

  it("shows at least 8:00 to 20:00, more when the salon opens earlier", () => {
    const agenda = {
      opening: [{ weekday: 0, opens_at: "07:00", closes_at: "19:00" }],
      staff: [],
    } as unknown as Parameters<typeof gridRange>[0];
    expect(gridRange(agenda, [], BENIN)).toEqual([420, 1200]);
  });
});

const PAGE: BookingPage = {
  pro: PRO,
  services: [
    {
      id: "s1",
      name: "Coloration",
      description: "",
      price_kind: "fixed",
      price_minor: 20000,
      currency: "XOF",
      duration_minutes: 120,
      work_minutes: 60,
      deposit_minor: 0,
      category_id: null,
      options: [],
    },
  ],
  staff: [{ id: "st1", name: "Estelle", color: "#C8102E", photo: null, service_ids: [] }],
  accepts_guests: true,
  auto_confirm: true,
  free_cancel_hours: 24,
  last_minute: null,
  first_day: "2030-01-07",
  last_day: "2030-03-07",
};

const ICONS = {
  clock: null,
  person: null,
  calendar: null,
  bell: null,
  group: null,
  lightning: null,
};

describe("BookingFlow", () => {
  beforeEach(() => {
    document.cookie = "sg_signed_in=; path=/; max-age=0";
  });

  it("lets a guest book a time with her name and number", async () => {
    const days = Array.from({ length: 7 }, (_, i) => ({
      day: addDays("2030-01-07", i),
      slots:
        i === 0
          ? [
              {
                start: "2030-01-07T09:00:00+00:00",
                end: "2030-01-07T11:00:00+00:00",
                staff_id: "st1",
                discount_percent: 0,
              },
            ]
          : [],
    }));
    const fetchMock = mockApi([
      { path: "/pros/salon-estelle/booking/slots", body: { days, next_day: "2030-01-14" } },
      {
        method: "POST",
        path: "/pros/salon-estelle/booking",
        status: 201,
        body: { appointment: appointment(), manage_url: "/rdv/secret", checkout_url: null },
      },
    ]);
    renderWithProviders(
      <BookingFlow page={PAGE} slug="salon-estelle" initialServiceId="s1" icons={ICONS} />,
    );
    await userEvent.click(await screen.findByRole("button", { name: /^10\sh$/ }));
    await userEvent.type(screen.getByLabelText("Ton prénom"), "Inès");
    await userEvent.type(screen.getByLabelText(/Ton numéro WhatsApp/), "0197000001");
    await userEvent.click(
      screen.getByRole("button", { name: /^Réserver lundi 7 janvier à 10\sh$/ }),
    );
    await waitFor(() =>
      expect(sentBody(fetchMock, "/pros/salon-estelle/booking")).toMatchObject({
        service_id: "s1",
        start: "2030-01-07T09:00:00+00:00",
        guest_name: "Inès",
        guest_phone: "0197000001",
      }),
    );
    expect(await screen.findByRole("heading", { name: "C'est réservé !" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Voir mon rendez-vous" })).toHaveAttribute(
      "href",
      "/fr/rdv/secret",
    );
  });

  it("offers the waiting list when the day is full", async () => {
    const days = Array.from({ length: 7 }, (_, i) => ({
      day: addDays("2030-01-07", i),
      slots: [],
    }));
    mockApi([{ path: "/pros/salon-estelle/booking/slots", body: { days, next_day: null } }]);
    renderWithProviders(
      <BookingFlow page={PAGE} slug="salon-estelle" initialServiceId="s1" icons={ICONS} />,
    );
    expect(
      await screen.findByRole("button", { name: "Préviens-moi si une place se libère" }),
    ).toBeVisible();
  });
});

describe("AppointmentView", () => {
  it("lets a guest accept another time with her link", async () => {
    const proposed = appointment({
      status: "proposed",
      proposed_from: "2030-01-07T08:00:00+00:00",
      pro_message: "Plutôt à 10 h ?",
    });
    const fetchMock = mockApi([
      { path: "/booking/manage/secret", body: proposed },
      {
        method: "POST",
        path: "/booking/manage/secret/answer",
        body: { ...proposed, status: "confirmed" },
      },
    ]);
    renderWithProviders(<AppointmentView holder={{ token: "secret" }} />);
    expect(await screen.findByText("« Plutôt à 10 h ? »")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "J'accepte ce créneau" }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/booking/manage/secret/answer")).toEqual({ accept: true }),
    );
  });
});
