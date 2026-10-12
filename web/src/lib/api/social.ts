/** Social network: feed, posts, comments, follows, stories, reviews, moderation. */
import { api, unwrap, type Schemas } from "./client";

// Light calls used by the feed live apart, so the home page does not download the rest.
export { follow, getFeed, getPersonPosts, getSaved, like, markStorySeen, save } from "./feed";

export type Post = Schemas["Post"];
export type PostPage = Schemas["PostPage"];
export type Author = Schemas["Author"];
export type Comment = Schemas["Comment"];
export type Reply = Schemas["Reply"];
export type StoryGroup = Schemas["StoryGroup"];
export type Story = Schemas["Story"];
export type Review = Schemas["Review"];
export type ReviewPage = Schemas["ReviewPage"];
export type PendingReview = Schemas["PendingReview"];
export type Following = Schemas["Following"];
export type PostInput = Schemas["PostCreateRequest"];
export type StoryInput = Schemas["StoryCreateRequest"];
export type ReportReason = Schemas["ReportRequest"]["reason"];
export type TargetKind = Schemas["TargetRequest"]["target"];
export type ShareNetwork = Schemas["ShareRequestRequest"]["network"];

export const createPost = (body: PostInput) => unwrap(api.POST("/api/v1/posts", { body }));

export const getPost = (id: string) =>
  unwrap(api.GET("/api/v1/posts/{post_id}", { params: { path: { post_id: id } } }));

export const updatePost = (id: string, body: Schemas["PatchedPostUpdateRequest"]) =>
  unwrap(api.PATCH("/api/v1/posts/{post_id}", { params: { path: { post_id: id } }, body }));

export const deletePost = (id: string) =>
  unwrap(api.DELETE("/api/v1/posts/{post_id}", { params: { path: { post_id: id } } }));

export const getMyPosts = (status?: string) =>
  unwrap(api.GET("/api/v1/me/posts", { params: { query: status ? { status } : {} } }));

export const share = (id: string, network: ShareNetwork) =>
  unwrap(
    api.POST("/api/v1/posts/{post_id}/share", {
      params: { path: { post_id: id } },
      body: { network },
    }),
  );

export const getComments = (postId: string, cursor?: string) =>
  unwrap(
    api.GET("/api/v1/posts/{post_id}/comments", {
      params: { path: { post_id: postId }, query: cursor ? { cursor } : {} },
    }),
  );

export const addComment = (postId: string, text: string, parentId?: string) =>
  unwrap(
    api.POST("/api/v1/posts/{post_id}/comments", {
      params: { path: { post_id: postId } },
      body: { text, ...(parentId ? { parent_id: parentId } : {}) },
    }),
  );

export const deleteComment = (id: string) =>
  unwrap(api.DELETE("/api/v1/comments/{comment_id}", { params: { path: { comment_id: id } } }));

export const getFollowing = () => unwrap(api.GET("/api/v1/me/following"));

export const getStories = (city?: string) =>
  unwrap(api.GET("/api/v1/stories", { params: { query: city ? { city } : {} } }));

export const createStory = (body: StoryInput) => unwrap(api.POST("/api/v1/stories", { body }));

export const deleteStory = (id: string) =>
  unwrap(api.DELETE("/api/v1/stories/{story_id}", { params: { path: { story_id: id } } }));

export const getReviews = (slug: string, cursor?: string) =>
  unwrap(
    api.GET("/api/v1/pros/{slug}/reviews", {
      params: { path: { slug }, query: cursor ? { cursor } : {} },
    }),
  );

export const getPendingReviews = () => unwrap(api.GET("/api/v1/me/reviews/pending"));

export const createReview = (body: Schemas["ReviewCreateRequest"]) =>
  unwrap(api.POST("/api/v1/reviews", { body }));

export const replyToReview = (id: string, text: string) =>
  unwrap(
    api.POST("/api/v1/reviews/{review_id}/reply", {
      params: { path: { review_id: id } },
      body: { text },
    }),
  );

export const report = (target: TargetKind, id: string, reason: ReportReason, comment = "") =>
  unwrap(api.POST("/api/v1/reports", { body: { target, id, reason, comment } }));

export const hide = (target: TargetKind, id: string) =>
  unwrap(api.POST("/api/v1/hides", { body: { target, id } }));

export const block = (userId: string, on: boolean) =>
  unwrap(
    on
      ? api.POST("/api/v1/people/{user_id}/block", { params: { path: { user_id: userId } } })
      : api.DELETE("/api/v1/people/{user_id}/block", { params: { path: { user_id: userId } } }),
  );

/** Uploads a picture or video for a post or a story; processed in the background. */
export function uploadMedia(
  file: File,
  purpose: "post" | "story" | "review_photo" | "review_voice",
) {
  const form = new FormData();
  form.append("file", file);
  form.append("purpose", purpose);
  return unwrap(
    api.POST("/api/v1/media", { body: form as unknown as Schemas["MediaUploadRequest"] }),
  );
}

export const getMedia = (id: string) =>
  unwrap(api.GET("/api/v1/media/{asset_id}", { params: { path: { asset_id: id } } }));
