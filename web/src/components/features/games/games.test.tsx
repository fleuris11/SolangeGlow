import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import type { DailyQuiz, GlowMe, Poll, Wheel } from "@/lib/api/games";
import { REFERRAL_KEY } from "@/lib/api/games";
import { called, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { CheckIn } from "./check-in";
import { MyPoints } from "./my-points";
import { PollCard } from "./polls";
import { DailyQuizScreen } from "./quiz";
import { WheelScreen } from "./wheel";

const ME: GlowMe = {
  balance: 1458,
  earned_total: 1458,
  level: "star",
  next_level: "icon",
  next_level_at: 5000,
  multiplier: 1.1,
  streak: { streak: 5, best: 9, today_done: true, bonus_every: 7, to_bonus: 2 },
  referral: {
    code: "AWA12345",
    path: "/invite/AWA12345",
    invited: 2,
    rewarded: 1,
    referrer_points: 200,
    referee_points: 100,
  },
  scale: [
    { action: "checkin", points: 5, per_day: null, bonus: false },
    { action: "review", points: 20, per_day: 5, bonus: false },
    { action: "streak", points: 50, per_day: null, bonus: true },
  ],
  daily_max: 400,
  earned_today: 25,
  games_open: true,
  wheel_open: true,
};

beforeEach(() => {
  document.cookie = "sg_signed_in=1; path=/";
  window.localStorage.clear();
});

describe("MyPoints", () => {
  it("shows the balance, the level, the streak and exchanges points", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi([
      { path: "/glow/me", body: ME },
      {
        path: "/glow/rewards",
        body: [
          {
            id: "r1",
            title: "-1 000 FCFA sur la Sélection France",
            description: "",
            kind: "amount_off",
            cost_points: 500,
            amount_off_minor: 1000,
            course: null,
            min_level: "glow",
            locked: false,
            sold_out: false,
            affordable: true,
          },
          {
            id: "r2",
            title: "Grande réduction",
            description: "",
            kind: "amount_off",
            cost_points: 4000,
            amount_off_minor: 5000,
            course: null,
            min_level: "icon",
            locked: true,
            sold_out: false,
            affordable: false,
          },
        ],
      },
      { path: "/glow/vouchers", body: [] },
      { path: "/glow/history", body: [] },
      {
        method: "POST",
        path: "/glow/rewards/r1/redeem",
        body: {
          balance: 958,
          course: null,
          voucher: {
            id: "v1",
            code: "GLOW-ABC234",
            kind: "amount_off",
            origin: "reward",
            label: "1 000 FCFA de réduction",
            amount_off_minor: 1000,
            currency: "XOF",
            expires_at: "2026-12-01T10:00:00Z",
            used_at: null,
          },
        },
      },
    ]);
    renderWithProviders(<MyPoints />);
    expect(await screen.findByText(/1.458/)).toBeInTheDocument();
    expect(screen.getByText("Star")).toBeInTheDocument();
    expect(screen.getByText(/Encore 3.542 points pour être Icône/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "5 jours d'affilée" })).toBeInTheDocument();
    expect(screen.getByText(/Encore 2 jours pour 50 points bonus/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Dès le niveau Icône" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /Échanger \(500 points\)/ }));
    expect(await screen.findByText("GLOW-ABC234")).toBeInTheDocument();
    expect(called(fetchMock, "/glow/rewards/r1/redeem", "POST")).toBe(true);
  });
});

describe("CheckIn", () => {
  it("records today's visit and links a waiting invitation", async () => {
    window.localStorage.setItem(REFERRAL_KEY, "AWA12345");
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/glow/check-in",
        body: {
          streak: 7,
          best: 7,
          today_done: true,
          bonus_every: 7,
          to_bonus: 7,
          already: false,
          gained: 5,
          bonus: 50,
          balance: 300,
        },
      },
      { method: "POST", path: "/glow/referral", status: 201 },
    ]);
    renderWithProviders(<CheckIn streak={6} done={false} flame={<span />} />);
    expect(await screen.findByText(/Bonus de série ! \+55 points \(7 jours\)/)).toBeInTheDocument();
    expect(screen.getByText("7 jours d'affilée")).toBeInTheDocument();
    expect(sentBody(fetchMock, "/glow/referral")).toEqual({ code: "AWA12345" });
    await waitFor(() => expect(window.localStorage.getItem(REFERRAL_KEY)).toBeNull());
  });

  it("does nothing more once the visit of the day is counted", async () => {
    const fetchMock = mockApi([]);
    renderWithProviders(<CheckIn streak={3} done flame={<span />} />);
    expect(screen.getByText("3 jours d'affilée")).toBeInTheDocument();
    await act(async () => undefined);
    expect(called(fetchMock, "/glow/check-in", "POST")).toBe(false);
  });
});

const QUIZ: DailyQuiz = {
  date: "2026-11-02",
  points_per_answer: 10,
  score: 0,
  answered: 0,
  questions: [
    {
      id: "q1",
      position: 0,
      text: "Quel beurre vient du nord du Bénin ?",
      choices: ["Le karité", "Le cacao", "L'argan"],
      image: null,
      audio: null,
      answered: null,
      correct: null,
      answer: null,
      explanation: "",
    },
  ],
};

describe("DailyQuizScreen", () => {
  it("answers a question with big buttons and tells the points", async () => {
    const user = userEvent.setup();
    mockApi([
      { path: "/glow/quiz", body: { quiz: QUIZ } },
      {
        method: "POST",
        path: "/glow/quiz/q1/answer",
        body: { correct: true, answer: 1, explanation: "Le karité nourrit.", gained: 10 },
      },
    ]);
    renderWithProviders(<DailyQuizScreen />);
    expect(await screen.findByText(/1 sur 1/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Le karité" }));
    expect(await screen.findByText("Bonne réponse ! +10 points")).toBeInTheDocument();
    expect(screen.getByText("Le karité nourrit.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Voir mon score" })).toBeInTheDocument();
  });

  it("invites to come back when there is no quiz", async () => {
    mockApi([{ path: "/glow/quiz", body: { quiz: null } }]);
    renderWithProviders(<DailyQuizScreen />);
    expect(await screen.findByText("Pas de quiz aujourd'hui")).toBeInTheDocument();
  });
});

const WHEEL: Wheel = {
  open: true,
  can_spin: true,
  today: null,
  prizes: [
    { id: "p1", label: "10 points", kind: "points", chance: "75.0" },
    { id: "p2", label: "À demain !", kind: "nothing", chance: "25.0" },
  ],
};

describe("WheelScreen", () => {
  it("spins for free, shows the prize drawn by the server and the chances", async () => {
    const user = userEvent.setup();
    window.matchMedia = ((query: string) => ({
      matches: query.includes("reduce"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    })) as unknown as typeof window.matchMedia;
    mockApi([
      { path: "/glow/wheel", body: WHEEL },
      {
        method: "POST",
        path: "/glow/wheel/spin",
        body: { prize_id: "p1", label: "10 points", kind: "points", points: 10, voucher: null },
      },
    ]);
    renderWithProviders(<WheelScreen />);
    expect(await screen.findByText("75 %")).toBeInTheDocument();
    expect(screen.getByText(/Jamais payant, aucun achat demandé/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Tourner la roue \(gratuit\)/ }));
    expect(await screen.findByText("Tu gagnes : 10 points")).toBeInTheDocument();
  });
});

const POLL: Poll = {
  id: "poll1",
  caption: "Tresses ou locks ?",
  author: {
    id: "u1",
    name: "Fifamè",
    photo: null,
    is_pro: false,
    pro_slug: null,
    verified: false,
    has_story: false,
    followed: false,
  },
  photo_a: null,
  photo_b: null,
  label_a: "Tresses",
  label_b: "Locks",
  ends_at: new Date(Date.now() + 5 * 3_600_000).toISOString(),
  ended: false,
  mine: false,
  my_vote: null,
  result: null,
};

function LivePoll() {
  const [poll, setPoll] = useState(POLL);
  return <PollCard poll={poll} onChange={setPoll} />;
}

describe("PollCard", () => {
  it("hides the result until she votes, then shows the shares", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/glow/polls/poll1/vote",
        body: { ...POLL, my_vote: "b", result: { total: 4, a: 25, b: 75 } },
      },
    ]);
    renderWithProviders(<LivePoll />);
    expect(screen.getByText("Touche la photo que tu préfères.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voter pour Locks" }));
    expect(sentBody(fetchMock, "/glow/polls/poll1/vote")).toEqual({ choice: "b" });
    expect(await screen.findByText("75 %")).toBeInTheDocument();
    expect(screen.getByText("Ton choix")).toBeInTheDocument();
    expect(screen.getByText("4 votes")).toBeInTheDocument();
  });
});
