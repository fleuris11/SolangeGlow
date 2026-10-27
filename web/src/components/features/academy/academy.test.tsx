import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { CourseDetail } from "@/lib/api/academy";
import { called, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { BuySheet } from "./buy-sheet";
import { PassScreen } from "./pass-screen";
import { QuizScreen } from "./quiz-screen";

const MODULE = "8f3c2a8e-0000-4000-8000-000000000001";

function course(overrides: Partial<CourseDetail> = {}): CourseDetail {
  return {
    id: "8f3c2a8e-0000-4000-8000-000000000002",
    slug: "maquillage-mariee",
    title: "Maquillage mariée",
    summary: "Un teint qui tient",
    cover: null,
    trade: "makeup",
    trade_name: "Maquillage",
    level: "beginner",
    language: "fr",
    pricing: "paid",
    price_minor: 5000,
    currency: "XOF",
    duration_seconds: 1200,
    lessons_count: 4,
    students_count: 0,
    trainer: {
      name: "Institut Prisca",
      slug: "institut-prisca",
      photo: null,
      platform: false,
      trained: false,
    },
    status: "published",
    description: "",
    country: "BJ",
    published_at: null,
    modules: [],
    enrollment: null,
    is_trainer: false,
    pass_offer: { price_minor: 2000, currency: "XOF", active: false },
    refund_days: 14,
    ...overrides,
  } as CourseDetail;
}

describe("QuizScreen", () => {
  it("sends one answer per question and shows the score", async () => {
    const fetchMock = mockApi([
      {
        path: `/academy/modules/${MODULE}/quiz`,
        body: {
          module_id: MODULE,
          module_title: "Préparer la peau",
          course_slug: "maquillage-mariee",
          questions: [
            { id: "q1", text: "Avant le fond de teint ?", choices: ["Hydrater", "Poudrer"] },
            { id: "q2", text: "On fixe avec ?", choices: ["De l'eau", "De la poudre"] },
          ],
          unlocked: true,
          passed: false,
          last_score: null,
          pass_percent: 70,
        },
      },
      {
        method: "POST",
        path: `/academy/modules/${MODULE}/quiz`,
        body: {
          score_percent: 100,
          passed: true,
          pass_percent: 70,
          results: [
            { question: "q1", right: true, correct: 0 },
            { question: "q2", right: true, correct: 1 },
          ],
          progress: { progress_percent: 100, completed: true, certificate: "ABCD-EFGH-JKLM" },
        },
      },
    ]);
    renderWithProviders(<QuizScreen slug="maquillage-mariee" moduleId={MODULE} />);
    expect(await screen.findByRole("radiogroup", { name: /Avant le fond de teint/ })).toBeVisible();
    const submit = screen.getByRole("button", { name: "Valider mes réponses" });
    expect(submit).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: "Hydrater" }));
    await userEvent.click(screen.getByRole("radio", { name: "De la poudre" }));
    await userEvent.click(submit);
    expect(await screen.findByText("Réussi : 100 % de bonnes réponses !")).toBeVisible();
    expect(sentBody(fetchMock, `/academy/modules/${MODULE}/quiz`)).toEqual({ answers: [0, 1] });
    expect(screen.getByText(/ton certificat est prêt/)).toBeVisible();
  });
});

describe("BuySheet", () => {
  it("asks for the waiver before paying", async () => {
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/academy/courses/maquillage-mariee/get",
        body: { enrollment: null, checkout_url: null },
      },
    ]);
    renderWithProviders(
      <BuySheet
        course={course()}
        price="5 000 FCFA"
        open
        onOpenChange={() => undefined}
        onError={() => undefined}
      />,
    );
    const pay = await screen.findByRole("button", { name: "Payer 5 000 FCFA" });
    expect(pay).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /Je renonce à mon droit/ }));
    expect(pay).toBeEnabled();
    await userEvent.click(pay);
    await waitFor(() =>
      expect(sentBody(fetchMock, "/academy/courses/maquillage-mariee/get")).toMatchObject({
        waiver: true,
        waiver_text: expect.stringContaining("14 jours"),
      }),
    );
  });
});

describe("PassScreen", () => {
  it("shows the monthly price and opens the payment", async () => {
    const fetchMock = mockApi([
      {
        path: "/academy/pass",
        body: {
          status: "ended",
          active: false,
          current_period_end: null,
          cancel_at_period_end: false,
          payment_due: false,
          price_minor: 2000,
          currency: "XOF",
        },
      },
      { method: "POST", path: "/academy/pass/subscribe", body: { checkout_url: "" } },
    ]);
    renderWithProviders(<PassScreen />);
    expect(await screen.findByText(/2\s000 FCFA par mois/)).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /Prendre le pass/ }));
    await waitFor(() => expect(called(fetchMock, "/academy/pass/subscribe", "POST")).toBe(true));
  });
});
