/** Academy: catalogue, courses, player, quizzes, certificates, pass, lives, trainer space. */
import { ApiError, api, CLIENT_HEADER, refreshSession, unwrap, type Schemas } from "./client";

export type CourseCard = Schemas["CourseCard"];
export type CourseDetail = Schemas["CourseDetail"];
export type MyEnrollment = Schemas["MyEnrollment"];
export type LessonPlayback = Schemas["LessonPlayback"];
export type Quiz = Schemas["Quiz"];
export type QuizResult = Schemas["QuizResult"];
export type MyAcademy = Schemas["MyAcademy"];
export type AcademyPass = Schemas["AcademyPass"];
export type Live = Schemas["Live"];
export type LiveRoom = Schemas["LiveRoom"];
export type Studio = Schemas["Studio"];
export type StudioCourse = Schemas["StudioCourse"];
export type StudioModule = Schemas["StudioModule"];
export type StudioLesson = Schemas["StudioLesson"];
export type CourseLevel = Schemas["CourseLevelEnum"];
export type CoursePricing = Schemas["CoursePricingEnum"];

// --- Courses -------------------------------------------------------------------------------------

export const getCourse = (slug: string) =>
  unwrap(api.GET("/api/v1/academy/courses/{slug}", { params: { path: { slug } } }));
export const takeCourse = (slug: string, body: Schemas["GetCourseRequest"]) =>
  unwrap(api.POST("/api/v1/academy/courses/{slug}/get", { params: { path: { slug } }, body }));
export const refundCourse = (enrollmentId: string) =>
  unwrap(
    api.POST("/api/v1/academy/enrollments/{enrollment_id}/refund", {
      params: { path: { enrollment_id: enrollmentId } },
    }),
  );

// --- Player and quiz -----------------------------------------------------------------------------

export const getLesson = (lessonId: string) =>
  unwrap(
    api.GET("/api/v1/academy/lessons/{lesson_id}", { params: { path: { lesson_id: lessonId } } }),
  );
export const savePosition = (lessonId: string, body: Schemas["PositionRequest"]) =>
  unwrap(
    api.POST("/api/v1/academy/lessons/{lesson_id}/position", {
      params: { path: { lesson_id: lessonId } },
      body,
    }),
  );
export const getQuiz = (moduleId: string) =>
  unwrap(
    api.GET("/api/v1/academy/modules/{module_id}/quiz", {
      params: { path: { module_id: moduleId } },
    }),
  );
export const answerQuiz = (moduleId: string, answers: number[]) =>
  unwrap(
    api.POST("/api/v1/academy/modules/{module_id}/quiz", {
      params: { path: { module_id: moduleId } },
      body: { answers },
    }),
  );

// --- My courses, certificates, pass --------------------------------------------------------------

export const getMyAcademy = () => unwrap(api.GET("/api/v1/academy/me"));
export const certificatePdfUrl = (code: string) =>
  `/api/v1/academy/me/certificates/${encodeURIComponent(code)}.pdf`;
export const getPass = () => unwrap(api.GET("/api/v1/academy/pass"));
export const subscribePass = () => unwrap(api.POST("/api/v1/academy/pass/subscribe"));
export const cancelPass = () => unwrap(api.POST("/api/v1/academy/pass/cancel"));

// --- Lives ---------------------------------------------------------------------------------------

export const getLives = () => unwrap(api.GET("/api/v1/academy/lives"));
export const getLiveRoom = (liveId: string) =>
  unwrap(api.GET("/api/v1/academy/lives/{live_id}", { params: { path: { live_id: liveId } } }));
export const registerLive = (liveId: string) =>
  unwrap(
    api.POST("/api/v1/academy/lives/{live_id}/registration", {
      params: { path: { live_id: liveId } },
    }),
  );
export const unregisterLive = (liveId: string) =>
  unwrap(
    api.DELETE("/api/v1/academy/lives/{live_id}/registration", {
      params: { path: { live_id: liveId } },
    }),
  );
export const joinLive = (liveId: string) =>
  unwrap(
    api.POST("/api/v1/academy/lives/{live_id}/join", { params: { path: { live_id: liveId } } }),
  );

// --- Trainer space -------------------------------------------------------------------------------

export const getStudio = () => unwrap(api.GET("/api/v1/academy/studio"));
export const createCourse = (body: Schemas["NewCourseRequest"]) =>
  unwrap(api.POST("/api/v1/academy/studio/courses", { body }));
export const getStudioCourse = (courseId: string) =>
  unwrap(
    api.GET("/api/v1/academy/studio/courses/{course_id}", {
      params: { path: { course_id: courseId } },
    }),
  );
export const updateCourse = (courseId: string, body: Schemas["PatchedCourseInputRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/academy/studio/courses/{course_id}", {
      params: { path: { course_id: courseId } },
      body,
    }),
  );
export const submitCourse = (courseId: string) =>
  unwrap(
    api.POST("/api/v1/academy/studio/courses/{course_id}/submit", {
      params: { path: { course_id: courseId } },
    }),
  );
export const archiveCourse = (courseId: string) =>
  unwrap(
    api.POST("/api/v1/academy/studio/courses/{course_id}/archive", {
      params: { path: { course_id: courseId } },
    }),
  );
export const addModule = (courseId: string, title: string) =>
  unwrap(
    api.POST("/api/v1/academy/studio/courses/{course_id}/modules", {
      params: { path: { course_id: courseId } },
      body: { title },
    }),
  );
export const renameModule = (moduleId: string, title: string) =>
  unwrap(
    api.PATCH("/api/v1/academy/studio/modules/{module_id}", {
      params: { path: { module_id: moduleId } },
      body: { title },
    }),
  );
export const deleteModule = (moduleId: string) =>
  unwrap(
    api.DELETE("/api/v1/academy/studio/modules/{module_id}", {
      params: { path: { module_id: moduleId } },
    }),
  );
export const addLesson = (moduleId: string, body: Schemas["LessonInputRequest"]) =>
  unwrap(
    api.POST("/api/v1/academy/studio/modules/{module_id}/lessons", {
      params: { path: { module_id: moduleId } },
      body,
    }),
  );
export const updateLesson = (lessonId: string, body: Schemas["PatchedLessonInputRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/academy/studio/lessons/{lesson_id}", {
      params: { path: { lesson_id: lessonId } },
      body,
    }),
  );
export const deleteLesson = (lessonId: string) =>
  unwrap(
    api.DELETE("/api/v1/academy/studio/lessons/{lesson_id}", {
      params: { path: { lesson_id: lessonId } },
    }),
  );
export const addResource = (lessonId: string, body: Schemas["CourseResourceInputRequest"]) =>
  unwrap(
    api.POST("/api/v1/academy/studio/lessons/{lesson_id}/resources", {
      params: { path: { lesson_id: lessonId } },
      body,
    }),
  );
export const deleteResource = (resourceId: string) =>
  unwrap(
    api.DELETE("/api/v1/academy/studio/resources/{resource_id}", {
      params: { path: { resource_id: resourceId } },
    }),
  );
export const addQuestion = (moduleId: string, body: Schemas["QuestionInputRequest"]) =>
  unwrap(
    api.POST("/api/v1/academy/studio/modules/{module_id}/questions", {
      params: { path: { module_id: moduleId } },
      body,
    }),
  );
export const deleteQuestion = (questionId: string) =>
  unwrap(
    api.DELETE("/api/v1/academy/studio/questions/{question_id}", {
      params: { path: { question_id: questionId } },
    }),
  );
export const planLive = (body: Schemas["LiveInputRequest"]) =>
  unwrap(api.POST("/api/v1/academy/studio/lives", { body }));
export const cancelLive = (liveId: string) =>
  unwrap(
    api.POST("/api/v1/academy/studio/lives/{live_id}/cancel", {
      params: { path: { live_id: liveId } },
    }),
  );

// --- Files of a course (cover, lesson videos, PDF) -----------------------------------------------

export type AcademyPurpose = "course_cover" | "lesson_video" | "course_resource";
export type UploadedMedia = Schemas["Media"];

function sendFile(
  file: File,
  purpose: AcademyPurpose,
  onProgress?: (share: number) => void,
): Promise<{ status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("purpose", purpose);
    const request = new XMLHttpRequest();
    request.open("POST", "/api/v1/media");
    request.withCredentials = true;
    for (const [name, value] of Object.entries(CLIENT_HEADER))
      request.setRequestHeader(name, value);
    request.setRequestHeader("Accept-Language", document.documentElement.lang || "fr");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };
    request.onload = () => {
      let body: unknown = {};
      try {
        body = JSON.parse(request.responseText || "{}");
      } catch {
        body = {};
      }
      resolve({ status: request.status, body });
    };
    request.onerror = () => reject(new ApiError(0, "network"));
    request.send(form);
  });
}

/** Sends a file of a course with its progress (a lesson video can be big). */
export async function uploadAcademyFile(
  file: File,
  purpose: AcademyPurpose,
  onProgress?: (share: number) => void,
): Promise<UploadedMedia> {
  let answer = await sendFile(file, purpose, onProgress);
  if (answer.status === 401 && (await refreshSession())) {
    answer = await sendFile(file, purpose, onProgress);
  }
  if (answer.status >= 400) {
    const body = answer.body as { code?: string; message?: string };
    throw new ApiError(answer.status, body.code ?? "error", body);
  }
  return answer.body as UploadedMedia;
}

export const getUpload = (id: string) =>
  unwrap(api.GET("/api/v1/media/{asset_id}", { params: { path: { asset_id: id } } }));
