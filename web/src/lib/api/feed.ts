/** The few calls of the feed, kept small for the first load of the home page (ADR-004). */
import { api, unwrap } from "./client";

export const getFeed = (query: { cursor?: string; city?: string } = {}) =>
  unwrap(api.GET("/api/v1/feed", { params: { query } }));

export const getSaved = (cursor?: string) =>
  unwrap(api.GET("/api/v1/me/saved", { params: { query: cursor ? { cursor } : {} } }));

export const getPersonPosts = (userId: string, cursor?: string) =>
  unwrap(
    api.GET("/api/v1/people/{user_id}/posts", {
      params: { path: { user_id: userId }, query: cursor ? { cursor } : {} },
    }),
  );

export const like = (id: string, on: boolean) =>
  unwrap(
    on
      ? api.POST("/api/v1/posts/{post_id}/like", { params: { path: { post_id: id } } })
      : api.DELETE("/api/v1/posts/{post_id}/like", { params: { path: { post_id: id } } }),
  );

export const save = (id: string, on: boolean) =>
  unwrap(
    on
      ? api.POST("/api/v1/posts/{post_id}/save", { params: { path: { post_id: id } } })
      : api.DELETE("/api/v1/posts/{post_id}/save", { params: { path: { post_id: id } } }),
  );

export const follow = (userId: string, on: boolean) =>
  unwrap(
    on
      ? api.POST("/api/v1/people/{user_id}/follow", { params: { path: { user_id: userId } } })
      : api.DELETE("/api/v1/people/{user_id}/follow", { params: { path: { user_id: userId } } }),
  );

export const markStorySeen = (id: string) =>
  unwrap(api.POST("/api/v1/stories/{story_id}/seen", { params: { path: { story_id: id } } }));
