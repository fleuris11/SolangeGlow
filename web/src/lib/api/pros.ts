/** Pros: search, map, showcases, and the pro's own showcase (« Ma vitrine »). */
import { api, unwrap, type Schemas } from "./client";
import type { operations } from "./schema";

export type Showcase = Schemas["Showcase"];
export type MyPro = Schemas["MyPro"];
export type ProCard = Schemas["Card"];
export type SearchResults = Schemas["SearchResults"];
export type Service = Schemas["Service"];
export type ServiceInput = Schemas["ServiceWriteRequest"];
export type Category = Schemas["Category"];
export type Period = Schemas["Period"];
export type Closure = Schemas["Closure"];
export type PortfolioItem = Schemas["PortfolioItem"];
export type MapConfig = Schemas["MapConfig"];
export type City = Schemas["City"];
export type VerificationState = Schemas["VerificationState"];
export type ProUpdate = Schemas["PatchedProUpdateRequest"];
export type SearchQuery = NonNullable<operations["pros_search"]["parameters"]["query"]>;
export type MapQuery = NonNullable<operations["pros_map_retrieve"]["parameters"]["query"]>;
export type MediaField = "photo" | "cover" | "bio_voice" | "landmarks_voice" | "itinerary_video";
export type PrintableName = "card.png" | "poster.pdf" | "stickers.pdf";

export const myProQueryKey = ["me", "pro"] as const;

// --- Public -------------------------------------------------------------------------------

export const searchPros = (query: SearchQuery) =>
  unwrap(api.GET("/api/v1/pros", { params: { query } }));

export const getMapPoints = (query: MapQuery) =>
  unwrap(api.GET("/api/v1/pros/map", { params: { query } }));

export const getPlaces = () => unwrap(api.GET("/api/v1/pros/places"));

export const getMapConfig = (country?: string) =>
  unwrap(api.GET("/api/v1/config/map", { params: { query: country ? { country } : {} } }));

export const getShowcase = (slug: string) =>
  unwrap(api.GET("/api/v1/pros/{slug}", { params: { path: { slug } } }));

export const announceArrival = (slug: string) =>
  unwrap(api.POST("/api/v1/pros/{slug}/arrival", { params: { path: { slug } } }));

/** Link of a QR code card, A4 poster or sticker sheet (served by the backend). */
export function printableUrl(slug: string, name: PrintableName, download = false): string {
  return `/api/v1/pros/${encodeURIComponent(slug)}/print/${name}${download ? "?download=1" : ""}`;
}

// --- My showcase --------------------------------------------------------------------------

export const getMyPro = () => unwrap(api.GET("/api/v1/me/pro"));

export const becomePro = (body: Schemas["BecomeProRequest"]) =>
  unwrap(api.POST("/api/v1/me/pro", { body }));

export const updateMyPro = (body: ProUpdate) => unwrap(api.PATCH("/api/v1/me/pro", { body }));

export const checkSlug = (slug: string) =>
  unwrap(api.GET("/api/v1/me/pro/slug", { params: { query: { slug } } }));

export function uploadProMedia(field: MediaField, file: Blob, name = "upload") {
  const form = new FormData();
  form.append("file", file, file instanceof File ? file.name : name);
  return unwrap(
    api.POST("/api/v1/me/pro/media/{field}", {
      params: { path: { field } },
      body: form as unknown as Schemas["FileUploadRequest"],
    }),
  );
}

export const removeProMedia = (field: MediaField) =>
  unwrap(api.DELETE("/api/v1/me/pro/media/{field}", { params: { path: { field } } }));

export const setMyLocation = (body: Schemas["LocationRequest"]) =>
  unwrap(api.PUT("/api/v1/me/pro/location", { body }));

export const setMyTravel = (body: Schemas["TravelUpdateRequest"]) =>
  unwrap(api.PUT("/api/v1/me/pro/travel", { body }));

export const publishMyPro = () => unwrap(api.POST("/api/v1/me/pro/publication"));
export const unpublishMyPro = () => unwrap(api.DELETE("/api/v1/me/pro/publication"));

export const listMyServices = () => unwrap(api.GET("/api/v1/me/pro/services"));

export const createService = (body: ServiceInput) =>
  unwrap(api.POST("/api/v1/me/pro/services", { body }));

export const updateService = (id: string, body: Schemas["PatchedServiceWriteRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/me/pro/services/{service_id}", {
      params: { path: { service_id: id } },
      body,
    }),
  );

export const deleteService = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/pro/services/{service_id}", { params: { path: { service_id: id } } }),
  );

export const createCategory = (name: string) =>
  unwrap(api.POST("/api/v1/me/pro/categories", { body: { name } }));

export const deleteCategory = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/pro/categories/{category_id}", {
      params: { path: { category_id: id } },
    }),
  );

export const getMyHours = () => unwrap(api.GET("/api/v1/me/pro/hours"));

export const saveMyHours = (periods: Schemas["PeriodRequest"][]) =>
  unwrap(api.PUT("/api/v1/me/pro/hours", { body: { periods } }));

export const addClosure = (body: Schemas["ClosureRequest"]) =>
  unwrap(api.POST("/api/v1/me/pro/closures", { body }));

export const deleteClosure = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/pro/closures/{closure_id}", { params: { path: { closure_id: id } } }),
  );

export const listMyPortfolio = () => unwrap(api.GET("/api/v1/me/pro/portfolio"));

export function addPortfolioItem(input: {
  file: File;
  before?: File | null;
  caption?: string;
  serviceId?: string | null;
}) {
  const form = new FormData();
  form.append("file", input.file);
  if (input.before) form.append("before", input.before);
  if (input.caption) form.append("caption", input.caption);
  if (input.serviceId) form.append("service_id", input.serviceId);
  return unwrap(
    api.POST("/api/v1/me/pro/portfolio", {
      body: form as unknown as Schemas["PortfolioUploadRequest"],
    }),
  );
}

export const updatePortfolioItem = (id: string, body: Schemas["PatchedPortfolioUpdateRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/me/pro/portfolio/{item_id}", { params: { path: { item_id: id } }, body }),
  );

export const deletePortfolioItem = (id: string) =>
  unwrap(api.DELETE("/api/v1/me/pro/portfolio/{item_id}", { params: { path: { item_id: id } } }));

export const getMyVerification = () => unwrap(api.GET("/api/v1/me/pro/verification"));

export function sendVerification(input: { documentType: string; document: File; selfie: File }) {
  const form = new FormData();
  form.append("document_type", input.documentType);
  form.append("document", input.document);
  form.append("selfie", input.selfie);
  return unwrap(
    api.POST("/api/v1/me/pro/verification", {
      body: form as unknown as Schemas["VerificationUploadRequest"],
    }),
  );
}
