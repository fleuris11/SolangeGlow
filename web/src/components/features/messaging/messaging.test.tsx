import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Conversation, Message } from "@/lib/api/messaging";
import { emit } from "@/lib/messaging/bus";
import * as outbox from "@/lib/messaging/outbox";
import { called, ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { ConversationList } from "./conversation-list";
import { MessageBubble } from "./message-bubble";
import { Thread } from "./thread";

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

const AICHA = {
  id: "u2",
  name: "Aïcha Tresses",
  photo: null,
  is_pro: true,
  pro_slug: "aicha",
  verified: true,
  online: true,
  last_seen: null,
};

const message = (overrides: Partial<Message> = {}): Message => ({
  id: "m1",
  conversation_id: "c1",
  sender_id: "u2",
  kind: "text",
  text: "Bonjour, je suis libre samedi",
  media: null,
  share: null,
  client_id: null,
  fraud_labels: [],
  is_automatic: false,
  state: "visible",
  created_at: "2026-10-12T10:00:00Z",
  ...overrides,
});

const CONVERSATION: Conversation = {
  id: "c1",
  kind: "direct",
  purpose: "chat",
  title: "Aïcha Tresses",
  people: [AICHA],
  status: "active",
  unread: 1,
  muted: false,
  is_closed: false,
  payment_warning: false,
  last_message: message(),
  last_message_at: "2026-10-12T10:00:00Z",
  receipts: { delivered_up_to: null, read_up_to: null },
  waiting_for_answer: false,
};

beforeAll(async () => {
  // Loaded on demand in the app: prepare them outside the timed waits.
  await import("./conversation-list");
  await import("./thread");
}, 30_000);

beforeEach(() => {
  window.localStorage.clear();
});

describe("ConversationList", () => {
  it("shows conversations with their last message, presence and unread count", async () => {
    signIn();
    mockApi([
      { path: "/me", body: ME },
      { path: "/conversations", body: { results: [CONVERSATION], next: null } },
      { path: "/me/messaging/unread", body: { count: 1, requests: 2 } },
    ]);
    renderWithProviders(<ConversationList />);
    const link = await screen.findByRole("link", { name: /Aïcha Tresses/ });
    expect(link).toHaveAttribute("href", "/fr/messages/c1");
    expect(within(link).getByText("Bonjour, je suis libre samedi")).toBeVisible();
    expect(within(link).getByText("1 message non lu")).toBeInTheDocument();
    expect(await screen.findByRole("tab", { name: "Demandes (2)" })).toBeVisible();
  });

  it("explains how to start when there is no conversation", async () => {
    signIn();
    mockApi([
      { path: "/me", body: ME },
      { path: "/conversations", body: { results: [], next: null } },
    ]);
    renderWithProviders(<ConversationList />);
    expect(await screen.findByText("Aucun message pour l'instant")).toBeVisible();
    expect(screen.getByText(/Écris à une pro depuis sa vitrine/)).toBeVisible();
  });
});

describe("MessageBubble", () => {
  it("warns about a payment outside the app and says when her message was read", () => {
    renderWithProviders(
      <>
        <MessageBubble
          message={message({ fraud_labels: ["phone"] })}
          mine={false}
          onReport={vi.fn()}
        />
        <MessageBubble
          message={message({ id: "m2", sender_id: "u1" })}
          mine
          delivery="read"
          onDelete={vi.fn()}
        />
      </>,
    );
    expect(screen.getByText(/ne paie jamais en dehors de l'appli/)).toBeVisible();
    expect(screen.getByText("Lu")).toBeVisible();
  });

  it("asks before reporting", async () => {
    const onReport = vi.fn();
    renderWithProviders(<MessageBubble message={message()} mine={false} onReport={onReport} />);
    await userEvent.click(screen.getByRole("button", { name: /Signaler/ }));
    expect(screen.getByText(/Elle pourra lire cette conversation/)).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Oui, signaler" }));
    expect(onReport).toHaveBeenCalled();
  });

  it("shows a deleted message without its text", () => {
    renderWithProviders(
      <MessageBubble message={message({ state: "deleted", text: "" })} mine={false} />,
    );
    expect(screen.getByText("Message supprimé")).toBeVisible();
  });
});

describe("Thread", () => {
  it("shows the conversation, sends a message and marks it read", async () => {
    signIn();
    const sent = message({ id: "m9", sender_id: "u1", text: "Super, à samedi !" });
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      { path: "/conversations/c1", body: CONVERSATION },
      { path: "/conversations/c1/messages", body: { results: [message()], next: null } },
      { method: "POST", path: "/conversations/c1/messages", status: 201, body: sent },
      { method: "POST", path: "/conversations/c1/read", status: 204 },
    ]);
    renderWithProviders(<Thread conversationId="c1" />);
    expect(await screen.findByRole("heading", { name: "Aïcha Tresses" })).toBeVisible();
    expect(screen.getByText("En ligne")).toBeVisible();
    expect(await screen.findByText("Bonjour, je suis libre samedi")).toBeVisible();
    await waitFor(() => expect(called(fetchMock, "/conversations/c1/read", "POST")).toBe(true));

    await userEvent.type(screen.getByLabelText("Ton message"), "Super, à samedi !");
    await userEvent.click(screen.getByRole("button", { name: /^Envoyer$/ }));
    expect(await screen.findByText("Super, à samedi !")).toBeVisible();
    const body = sentBody(fetchMock, "/conversations/c1/messages");
    expect(body).toMatchObject({ text: "Super, à samedi !" });
    expect(body?.client_id).toMatch(/^[0-9a-f-]{36}$/);
    await waitFor(() => expect(screen.getByText("Envoyé")).toBeVisible());
  });

  it("keeps a message written offline and sends it when the network is back", async () => {
    signIn();
    let online = false;
    const sent = message({ id: "m9", sender_id: "u1", text: "Tu es là ?" });
    mockApi([
      { path: "/me", body: ME },
      { path: "/conversations/c1", body: CONVERSATION },
      { path: "/conversations/c1/messages", body: { results: [], next: null } },
      { method: "POST", path: "/conversations/c1/read", status: 204 },
    ]);
    const realFetch = globalThis.fetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const request = input instanceof Request ? input : new Request(String(input), init);
        if (request.method === "POST" && request.url.endsWith("/conversations/c1/messages")) {
          if (!online) throw new TypeError("Failed to fetch");
          return new Response(JSON.stringify(sent), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          });
        }
        return realFetch(request);
      }),
    );
    renderWithProviders(<Thread conversationId="c1" />);
    await userEvent.type(await screen.findByLabelText("Ton message"), "Tu es là ?");
    await userEvent.click(screen.getByRole("button", { name: /^Envoyer$/ }));
    expect(await screen.findByText("En attente de connexion")).toBeVisible();
    expect(outbox.pendingFor("c1")).toHaveLength(1);

    online = true;
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    await waitFor(() => expect(outbox.pendingFor("c1")).toHaveLength(0));
    expect(screen.getByText("Tu es là ?")).toBeVisible();
  });

  it("receives live messages and typing, and shows the pay-in-the-app warning", async () => {
    signIn();
    mockApi([
      { path: "/me", body: ME },
      { path: "/conversations/c1", body: { ...CONVERSATION, payment_warning: true } },
      { path: "/conversations/c1/messages", body: { results: [], next: null } },
      { method: "POST", path: "/conversations/c1/read", status: 204 },
    ]);
    renderWithProviders(<Thread conversationId="c1" />);
    expect(await screen.findByText("Paie dans l'appli pour être protégée")).toBeVisible();
    act(() => emit({ type: "typing", conversation: "c1", user: "u2" }));
    expect(await screen.findByText("Aïcha Tresses écrit…")).toBeVisible();
    act(() => emit({ type: "message", message: message({ id: "m5", text: "Voici mes tarifs" }) }));
    expect(await screen.findByText("Voici mes tarifs")).toBeVisible();
  });

  it("lets her accept a message request", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      { path: "/conversations/c1", body: { ...CONVERSATION, status: "requested" } },
      { path: "/conversations/c1/messages", body: { results: [message()], next: null } },
      { method: "POST", path: "/conversations/c1/read", status: 204 },
      { method: "POST", path: "/conversations/c1/accept", body: CONVERSATION },
    ]);
    renderWithProviders(<Thread conversationId="c1" />);
    expect(await screen.findByText("Aïcha Tresses souhaite t'écrire")).toBeVisible();
    expect(screen.queryByLabelText("Ton message")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Accepter/ }));
    await waitFor(() => expect(called(fetchMock, "/conversations/c1/accept", "POST")).toBe(true));
    expect(await screen.findByLabelText("Ton message")).toBeVisible();
  });
});

describe("outbox", () => {
  it("marks refused messages as failed and stops on network errors", async () => {
    outbox.add({ clientId: "a", conversationId: "c1", body: { text: "1" }, createdAt: "" });
    outbox.add({ clientId: "b", conversationId: "c1", body: { text: "2" }, createdAt: "" });
    const refusal = new Error("refused");
    await outbox.flush(
      async (item) => {
        if (item.clientId === "a") throw refusal;
      },
      (error) => error === refusal,
    );
    expect(outbox.pendingFor("c1")).toEqual([
      expect.objectContaining({ clientId: "a", failed: true }),
    ]);

    outbox.add({ clientId: "c", conversationId: "c1", body: { text: "3" }, createdAt: "" });
    await outbox.flush(
      async () => {
        throw new TypeError("offline");
      },
      () => false,
    );
    expect(outbox.pendingFor("c1").map((p) => p.clientId)).toEqual(["a", "c"]);
  });
});
