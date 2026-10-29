/** The playful side (module 10): Glow Points, streak, quiz, wheel, « Help me choose »,
 * photo challenge, rewards, referral, routine, calendar and rankings. */
import { api, unwrap, type Schemas } from "./client";

export type GlowMe = Schemas["GlowMe"];
export type GlowToday = Schemas["GlowToday"];
export type GlowLevel = Schemas["GlowLevelEnum"];
export type GlowAction = Schemas["GlowActionEnum"];
export type GlowReward = Schemas["GlowReward"];
export type GlowVoucher = Schemas["GlowVoucher"];
export type GlowEntry = Schemas["GlowEntry"];
export type DailyQuiz = Schemas["DailyQuiz"];
export type DailyQuizQuestion = Schemas["DailyQuizQuestion"];
export type Wheel = Schemas["Wheel"];
export type WheelSpin = Schemas["WheelSpin"];
export type Poll = Schemas["Poll"];
export type Challenge = Schemas["Challenge"];
export type ChallengeEntry = Schemas["ChallengeEntry"];
export type Ranking = Schemas["Ranking"];
export type Routine = Schemas["Routine"];
export type Celebration = Schemas["Celebration"];
export type ProLevel = Schemas["ProLevelEnum"];

/** The invitation code kept between the link and the new account (referral). */
export const REFERRAL_KEY = "sg_referral";

export const getGlowMe = () => unwrap(api.GET("/api/v1/glow/me"));
export const getGlowToday = () => unwrap(api.GET("/api/v1/glow/today"));
export const checkIn = () => unwrap(api.POST("/api/v1/glow/check-in"));
export const getHistory = () => unwrap(api.GET("/api/v1/glow/history"));

export const getRewards = () => unwrap(api.GET("/api/v1/glow/rewards"));
export const redeemReward = (id: string) =>
  unwrap(
    api.POST("/api/v1/glow/rewards/{reward_id}/redeem", { params: { path: { reward_id: id } } }),
  );
export const getVouchers = () => unwrap(api.GET("/api/v1/glow/vouchers"));

export const getQuiz = () => unwrap(api.GET("/api/v1/glow/quiz"));
export const answerQuiz = (id: string, choice: number) =>
  unwrap(
    api.POST("/api/v1/glow/quiz/{question_id}/answer", {
      params: { path: { question_id: id } },
      body: { choice },
    }),
  );

export const getWheel = () => unwrap(api.GET("/api/v1/glow/wheel"));
export const spinWheel = () => unwrap(api.POST("/api/v1/glow/wheel/spin"));

export const getPolls = (scope: "vote" | "mine" = "vote") =>
  unwrap(api.GET("/api/v1/glow/polls", { params: { query: { scope } } }));
export const getPoll = (id: string) =>
  unwrap(api.GET("/api/v1/glow/polls/{poll_id}", { params: { path: { poll_id: id } } }));
export const createPoll = (body: Schemas["PollCreateRequest"]) =>
  unwrap(api.POST("/api/v1/glow/polls", { body }));
export const votePoll = (id: string, choice: "a" | "b") =>
  unwrap(
    api.POST("/api/v1/glow/polls/{poll_id}/vote", {
      params: { path: { poll_id: id } },
      body: { choice },
    }),
  );
export const deletePoll = (id: string) =>
  api.DELETE("/api/v1/glow/polls/{poll_id}", { params: { path: { poll_id: id } } });

export const getChallenge = () => unwrap(api.GET("/api/v1/glow/challenge"));
export const enterChallenge = (body: Schemas["ChallengeEnterRequest"]) =>
  unwrap(api.POST("/api/v1/glow/challenge/entries", { body }));
export const voteEntry = (id: string) =>
  unwrap(
    api.POST("/api/v1/glow/challenge/entries/{entry_id}/vote", {
      params: { path: { entry_id: id } },
    }),
  );

export const getRankings = (query: { city?: string; trade?: string }) =>
  unwrap(api.GET("/api/v1/glow/rankings", { params: { query } }));
export const getInvite = (code: string) =>
  unwrap(api.GET("/api/v1/glow/invite/{code}", { params: { path: { code } } }));
export const attachReferral = (code: string) =>
  unwrap(api.POST("/api/v1/glow/referral", { body: { code } }));

export const getRoutine = () => unwrap(api.GET("/api/v1/glow/routine"));
export const saveRoutine = (body: Schemas["RoutineStepsInputRequest"]) =>
  unwrap(api.PUT("/api/v1/glow/routine", { body }));
export const tickStep = (id: string, done: boolean) =>
  unwrap(
    api.POST("/api/v1/glow/routine/{step_id}", {
      params: { path: { step_id: id } },
      body: { done },
    }),
  );
export const saveReminders = (body: Schemas["RemindersInputRequest"]) =>
  unwrap(api.PUT("/api/v1/glow/reminders", { body }));
export const getCelebrations = () => unwrap(api.GET("/api/v1/glow/celebrations"));

/** A photo for « Help me choose » or the challenge; processed in the background. */
export function uploadGamePhoto(file: Blob, purpose: "poll_photo" | "challenge_photo") {
  const form = new FormData();
  form.append("file", file);
  form.append("purpose", purpose);
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}
