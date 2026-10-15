import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import type { Comment, Post, ReviewPage, StoryGroup } from "@/lib/api/social";
import { called, ME, mockApi, sentBody } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { Comments } from "./comments";
import { CreateFlow } from "./create-flow";
import { PostCard } from "./post-card";
import { ReviewsSection } from "./reviews-section";
import { StorySheet } from "./story-sheet";

function signIn() {
  document.cookie = "sg_signed_in=1; path=/";
}

const picture = (id: string) => ({
  id,
  kind: "image" as const,
  status: "ready" as const,
  error: null,
  blurhash: null,
  width: 800,
  height: 1000,
  duration: null,
  urls: { thumb: `/s3/${id}-thumb.webp`, medium: `/s3/${id}-medium.webp` },
});

const AUTHOR = {
  id: "u2",
  name: "Aïcha Tresses",
  photo: null,
  is_pro: true,
  pro_slug: "aicha",
  verified: true,
  has_story: false,
  followed: false,
};

const POST: Post = {
  id: "p1",
  kind: "photo",
  caption: "Knotless mi-dos",
  trade: null,
  service: { id: "s1", name: "Knotless" } as Post["service"],
  product_id: null,
  product: null,
  status: "published",
  publish_at: null,
  published_at: new Date(Date.now() - 3_600_000).toISOString(),
  visibility: "visible",
  city: "Cotonou",
  media: [{ role: "item", media: picture("m1") }],
  author: AUTHOR,
  like_count: 4,
  comment_count: 2,
  save_count: 0,
  share_count: 0,
  liked: false,
  saved: false,
  is_mine: false,
  share_url: "http://localhost:3000/p/p1",
};

describe("PostCard", () => {
  // The sheets are loaded on demand: prepare them once, outside the timed waits.
  beforeAll(async () => {
    await import("./post-sheets");
  }, 30_000);

  it("shows who posted, the picture, the caption and « Book this look »", () => {
    renderWithProviders(<PostCard post={POST} />);
    expect(screen.getByRole("article", { name: "Publication de Aïcha Tresses" })).toBeVisible();
    expect(screen.getByRole("img", { name: "Knotless mi-dos" })).toBeVisible();
    expect(screen.getByLabelText("Pro vérifiée")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Réserver ce look/ })).toHaveAttribute(
      "href",
      "/fr/aicha",
    );
  });

  it("labels both pictures of a before/after", () => {
    const post: Post = {
      ...POST,
      kind: "before_after",
      media: [
        { role: "before", media: picture("b") },
        { role: "after", media: picture("a") },
      ],
    };
    renderWithProviders(<PostCard post={post} />);
    expect(screen.getByRole("img", { name: "Avant : Knotless mi-dos" })).toBeVisible();
    expect(screen.getByRole("img", { name: "Après : Knotless mi-dos" })).toBeVisible();
  });

  it("sends visitors to sign in instead of liking", async () => {
    const fetchMock = mockApi([]);
    const router = (await import("next/navigation")).useRouter();
    renderWithProviders(<PostCard post={POST} />);
    await userEvent.click(screen.getByRole("button", { name: /J'aime \(4 j'aime\)/ }));
    expect(router.push).toHaveBeenCalledWith("/fr/auth");
    expect(fetchMock.records).toHaveLength(0);
  });

  it("likes at once and keeps the number given by the server", async () => {
    signIn();
    mockApi([
      {
        method: "POST",
        path: "/posts/p1/like",
        body: { like_count: 5, save_count: 0, liked: true, saved: false },
      },
    ]);
    renderWithProviders(<PostCard post={POST} />);
    const button = screen.getByRole("button", { name: /J'aime \(4 j'aime\)/ });
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(button).toHaveAccessibleName("Je n'aime plus (5 j'aime)"));
  });

  it("puts the like back when the server refuses it", async () => {
    signIn();
    mockApi([{ method: "POST", path: "/posts/p1/like", status: 403, body: { code: "blocked" } }]);
    renderWithProviders(<PostCard post={POST} />);
    const button = screen.getByRole("button", { name: /J'aime/ });
    await userEvent.click(button);
    await waitFor(() => expect(button).toHaveAttribute("aria-pressed", "false"));
    expect(button).toHaveAccessibleName("J'aime (4 j'aime)");
  });

  it("shares on WhatsApp, Facebook, TikTok or by copying the link", async () => {
    const whatsapp = "https://wa.me/?text=http%3A%2F%2Flocalhost%3A3000%2Fp%2Fp1";
    const fetchMock = mockApi([
      {
        method: "POST",
        path: "/posts/p1/share",
        body: { whatsapp, facebook: "https://www.facebook.com/sharer", url: POST.share_url },
      },
    ]);
    const open = vi.fn();
    vi.stubGlobal("open", open);
    renderWithProviders(<PostCard post={POST} />);
    await userEvent.click(screen.getByRole("button", { name: "Partager" }));
    const sheet = await screen.findByRole("dialog", { name: "Partager" });
    expect(within(sheet).getByRole("button", { name: /Facebook/ })).toBeVisible();
    expect(within(sheet).getByRole("button", { name: /TikTok/ })).toBeVisible();
    expect(within(sheet).getByRole("button", { name: /Copier le lien/ })).toBeVisible();
    await userEvent.click(within(sheet).getByRole("button", { name: /WhatsApp/ }));
    await waitFor(() => expect(open).toHaveBeenCalledWith(whatsapp, "_blank", "noopener"));
    expect(sentBody(fetchMock, "/posts/p1/share")).toEqual({ network: "whatsapp" });
  });

  it("reports a post with a reason", async () => {
    signIn();
    const fetchMock = mockApi([{ method: "POST", path: "/reports", status: 201, body: {} }]);
    renderWithProviders(<PostCard post={POST} />);
    await userEvent.click(screen.getByRole("button", { name: "Plus d'options" }));
    const sheet = await screen.findByRole("dialog", { name: "Options" });
    await userEvent.click(within(sheet).getByRole("button", { name: /Signaler/ }));
    await userEvent.click(await screen.findByRole("button", { name: /Arnaque/ }));
    await screen.findByText("Merci. Notre équipe va regarder.");
    expect(sentBody(fetchMock, "/reports")).toEqual({
      target: "post",
      id: "p1",
      reason: "scam",
      comment: "",
    });
  });
});

const COMMENT: Comment = {
  id: "c1",
  text: "Trop beau !",
  author: { ...AUTHOR, id: "u3", name: "Mariam", is_pro: false, pro_slug: null },
  created_at: new Date().toISOString(),
  is_mine: false,
  replies: [
    {
      id: "c2",
      text: "Merci ma belle",
      author: AUTHOR,
      created_at: new Date().toISOString(),
      is_mine: false,
    },
  ],
};

describe("Comments", () => {
  it("shows comments with their replies and invites visitors to sign in", async () => {
    mockApi([{ path: "/posts/p1/comments", body: { results: [COMMENT], next: null } }]);
    renderWithProviders(<Comments postId="p1" />);
    expect(await screen.findByText("Trop beau !")).toBeVisible();
    expect(screen.getByText("Merci ma belle")).toBeVisible();
    expect(screen.getByRole("link", { name: "Connecte-toi pour commenter" })).toBeVisible();
    expect(screen.queryByRole("button", { name: /Répondre/ })).not.toBeInTheDocument();
  });

  it("replies to a comment", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/posts/p1/comments", body: { results: [COMMENT], next: null } },
      { method: "POST", path: "/posts/p1/comments", status: 201, body: COMMENT },
    ]);
    renderWithProviders(<Comments postId="p1" />);
    await userEvent.click(await screen.findByRole("button", { name: /Répondre/ }));
    expect(screen.getByText(/Tu réponds à Mariam/)).toBeVisible();
    await userEvent.type(screen.getByLabelText("Ta réponse"), "Merci !");
    await userEvent.click(screen.getByRole("button", { name: /Envoyer/ }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/posts/p1/comments")).toEqual({
        text: "Merci !",
        parent_id: "c1",
      }),
    );
  });

  it("says when the post has no comment yet", async () => {
    mockApi([{ path: "/posts/p1/comments", body: { results: [], next: null } }]);
    renderWithProviders(<Comments postId="p1" />);
    expect(await screen.findByText("Aucun commentaire. Sois la première !")).toBeVisible();
  });
});

const STORY_BASE = {
  media: null,
  background: "hibiscus" as const,
  slots: [],
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 86_400_000).toISOString(),
  seen: false,
  is_mine: false,
};

const GROUPS: StoryGroup[] = [
  {
    author: { ...AUTHOR, has_story: true },
    seen: false,
    stories: [
      { ...STORY_BASE, id: "s1", kind: "free_slots", text: "", slots: ["14:00", "16:30"] },
      { ...STORY_BASE, id: "s2", kind: "text", text: "Promo tresses ce week-end" },
    ],
  },
];

describe("StorySheet", () => {
  it("shows free slots with a way to book, then the next story with the buttons", async () => {
    signIn();
    const fetchMock = mockApi([
      { method: "POST", path: "/stories/s1/seen", status: 204 },
      { method: "POST", path: "/stories/s2/seen", status: 204 },
    ]);
    const onShown = vi.fn();
    const onClose = vi.fn();
    renderWithProviders(
      <StorySheet groups={GROUPS} startAt={0} onShown={onShown} onClose={onClose} />,
    );
    const sheet = screen.getByRole("dialog", { name: "Aïcha Tresses" });
    expect(within(sheet).getByText("Story 1 sur 2")).toBeVisible();
    expect(within(sheet).getByText("Créneaux libres aujourd'hui")).toBeVisible();
    expect(within(sheet).getByText(/^14/)).toBeVisible();
    expect(
      within(sheet).getByRole("link", { name: /Voir sa vitrine pour réserver/ }),
    ).toBeVisible();
    expect(within(sheet).getByRole("button", { name: /Précédente/ })).toBeDisabled();

    await userEvent.click(within(sheet).getByRole("button", { name: /Suivante/ }));
    expect(within(sheet).getByText("Promo tresses ce week-end")).toBeVisible();
    await waitFor(() => expect(onShown).toHaveBeenCalledWith("u2"));
    expect(called(fetchMock, "/stories/s1/seen", "POST")).toBe(true);
    expect(called(fetchMock, "/stories/s2/seen", "POST")).toBe(true);

    await userEvent.click(within(sheet).getByRole("button", { name: /Terminer/ }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("ReviewsSection", () => {
  it("shows the average, the stars and the reply of the pro", () => {
    const page: ReviewPage = {
      count: 2,
      average: 4.5,
      distribution: { "5": 1, "4": 1, "3": 0, "2": 0, "1": 0 },
      next: null,
      results: [
        {
          id: "r1",
          rating: 5,
          text: "Très soigné",
          photo: null,
          voice: null,
          reply: "Merci Mariam",
          replied_at: new Date().toISOString(),
          author_name: "Mariam",
          author_photo: null,
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
    } as unknown as ReviewPage;
    renderWithProviders(<ReviewsSection page={page} name="Aïcha Tresses" />);
    expect(screen.getByText("4,5")).toBeVisible();
    expect(screen.getByText("2 avis vérifiés")).toBeVisible();
    expect(screen.getByText(/5 étoiles/)).toBeVisible();
    expect(screen.getByText("Réponse de Aïcha Tresses :")).toBeVisible();
  });

  it("explains that only real clients can rate", () => {
    const page = { count: 0, average: null, distribution: {}, next: null, results: [] };
    renderWithProviders(<ReviewsSection page={page as never} name="Aïcha Tresses" />);
    expect(screen.getByText("Aïcha Tresses n'a pas encore d'avis.")).toBeVisible();
    expect(screen.getByText(/Seules les clientes qui ont vraiment réservé/)).toBeVisible();
  });
});

describe("CreateFlow", () => {
  it("publishes a text story in three steps", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      { method: "POST", path: "/stories", status: 201, body: { id: "s9" } },
    ]);
    renderWithProviders(<CreateFlow />);
    expect(screen.getByRole("heading", { name: "Que veux-tu publier ?" })).toBeVisible();
    const next = screen.getByRole("button", { name: "Continuer" });
    expect(next).toBeDisabled();
    // Only pros can share their free slots.
    expect(screen.queryByRole("button", { name: "Créneaux libres" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Texte sur fond" }));
    await userEvent.click(next);
    expect(screen.getByRole("heading", { name: "Les détails" })).toBeVisible();
    await userEvent.type(screen.getByLabelText("Ton message"), "Dispo ce soir");
    await userEvent.click(screen.getByRole("button", { name: "Prune" }));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    expect(screen.getByRole("heading", { name: "Aperçu et publication" })).toBeVisible();
    expect(screen.getByText("Dispo ce soir")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Publier la story" }));
    await waitFor(() =>
      expect(sentBody(fetchMock, "/stories")).toEqual({
        kind: "text",
        text: "Dispo ce soir",
        background: "prune",
      }),
    );
  });

  it("uploads a picture, then schedules the post", async () => {
    signIn();
    const fetchMock = mockApi([
      { path: "/me", body: ME },
      {
        method: "POST",
        path: "/media",
        status: 201,
        body: { ...picture("m9"), status: "pending" },
      },
      { path: "/media/m9", body: picture("m9") },
      { method: "POST", path: "/posts", status: 201, body: { ...POST, id: "p9" } },
    ]);
    renderWithProviders(<CreateFlow />);
    await userEvent.click(screen.getByRole("button", { name: "Photo" }));
    const file = new File(["x"], "look.jpg", { type: "image/jpeg" });
    await userEvent.upload(screen.getByLabelText("Choisir dans ma galerie"), file);
    const next = screen.getByRole("button", { name: "Continuer" });
    await waitFor(() => expect(next).toBeEnabled());
    await userEvent.click(next);
    await userEvent.type(screen.getByLabelText("Légende"), "Mon look");
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    await userEvent.click(screen.getByRole("button", { name: "Plus tard" }));
    const schedule = screen.getByRole("button", { name: "Programmer" });
    expect(schedule).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Date et heure de publication"), "2026-12-01T10:00");
    await userEvent.click(schedule);
    await waitFor(() => expect(called(fetchMock, "/posts", "POST")).toBe(true));
    expect(sentBody(fetchMock, "/posts")).toMatchObject({
      kind: "photo",
      media: [{ id: "m9", role: "item" }],
      caption: "Mon look",
      status: "scheduled",
    });
  });
});
