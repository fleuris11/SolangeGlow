/** Help center and back office (module 12): FAQ, suggestions, tickets, invitations. */
import { api, unwrap, type Schemas } from "./client";

export type FaqTopic = Schemas["FaqTopic"];
export type FaqItem = Schemas["FaqItem"];
export type TicketInput = Schemas["TicketInputRequest"];

export const suggestAnswers = (question: string) =>
  unwrap(api.POST("/api/v1/help/suggest", { body: { question } }));
export const sendTicket = (body: TicketInput) => unwrap(api.POST("/api/v1/help/tickets", { body }));

/** Ends « sign in as » a member: the session of the member is closed too. */
export const stopImpersonation = () => unwrap(api.POST("/api/v1/backoffice/impersonation/stop"));

/** Links the new pro to the invitation she received (prospecting). */
export const claimInvitation = (code: string) =>
  unwrap(api.POST("/api/v1/prospects/claim", { body: { code } }));
