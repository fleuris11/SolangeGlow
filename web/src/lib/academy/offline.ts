/**
 * Lessons kept on the phone to watch without network (Academy).
 *
 * The low quality video is stored in its own cache (Cache API), under a stable address that
 * does not depend on the signed link. The service worker never empties this cache; the
 * student removes a lesson herself (« Mes formations » shows the space used).
 */

export const LESSONS_CACHE = "sg-lessons-v1";

export type OfflineLesson = {
  id: string;
  title: string;
  courseTitle: string;
  courseSlug: string;
  bytes: number;
  savedAt: string;
};

const keyOf = (lessonId: string) => `/offline/lessons/${lessonId}`;

export function offlineSupported(): boolean {
  return typeof window !== "undefined" && "caches" in window;
}

async function open(): Promise<Cache> {
  return window.caches.open(LESSONS_CACHE);
}

/** Downloads the video and keeps it; `onProgress` gets a share from 0 to 1. */
export async function saveLesson(
  lesson: Omit<OfflineLesson, "bytes" | "savedAt">,
  videoUrl: string,
  onProgress?: (share: number) => void,
): Promise<OfflineLesson> {
  const response = await fetch(videoUrl);
  if (!response.ok || !response.body) throw new Error(`download ${response.status}`);
  const total = Number(response.headers.get("Content-Length") ?? 0);
  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value);
    received += value.length;
    if (total && onProgress) onProgress(Math.min(1, received / total));
  }
  const blob = new Blob(parts as BlobPart[], { type: "video/mp4" });
  const saved: OfflineLesson = { ...lesson, bytes: blob.size, savedAt: new Date().toISOString() };
  const cache = await open();
  await cache.put(
    keyOf(lesson.id),
    new Response(blob, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Length": String(blob.size),
        "X-SG-Lesson": encodeURIComponent(JSON.stringify(saved)),
      },
    }),
  );
  onProgress?.(1);
  return saved;
}

export async function hasLesson(lessonId: string): Promise<boolean> {
  if (!offlineSupported()) return false;
  const cache = await open();
  return Boolean(await cache.match(keyOf(lessonId)));
}

/** A local address of the saved video (to give to the <video>), or null. */
export async function lessonBlobUrl(lessonId: string): Promise<string | null> {
  if (!offlineSupported()) return null;
  const cache = await open();
  const found = await cache.match(keyOf(lessonId));
  if (!found) return null;
  return URL.createObjectURL(await found.blob());
}

export async function removeLesson(lessonId: string): Promise<void> {
  if (!offlineSupported()) return;
  const cache = await open();
  await cache.delete(keyOf(lessonId));
}

export async function listLessons(): Promise<OfflineLesson[]> {
  if (!offlineSupported()) return [];
  const cache = await open();
  const lessons: OfflineLesson[] = [];
  for (const request of await cache.keys()) {
    const response = await cache.match(request);
    const meta = response?.headers.get("X-SG-Lesson");
    if (!meta) continue;
    try {
      lessons.push(JSON.parse(decodeURIComponent(meta)) as OfflineLesson);
    } catch {
      // a broken entry is simply not listed
    }
  }
  return lessons.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}
