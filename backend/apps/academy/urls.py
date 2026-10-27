from django.urls import path

from . import views

urlpatterns = [
    # Catalogue, course page, getting a course.
    path("academy/courses", views.CatalogueView.as_view(), name="academy-catalogue"),
    path("academy/courses/<slug:slug>", views.CourseView.as_view(), name="academy-course"),
    path("academy/courses/<slug:slug>/get", views.GetCourseView.as_view(), name="academy-get"),
    path(
        "academy/enrollments/<uuid:enrollment_id>/refund",
        views.RefundView.as_view(),
        name="academy-refund",
    ),
    # Player and quiz.
    path("academy/lessons/<uuid:lesson_id>", views.LessonView.as_view(), name="academy-lesson"),
    path(
        "academy/lessons/<uuid:lesson_id>/position",
        views.PositionView.as_view(),
        name="academy-position",
    ),
    path("academy/modules/<uuid:module_id>/quiz", views.QuizView.as_view(), name="academy-quiz"),
    # My courses, certificates, pass.
    path("academy/me", views.MyAcademyView.as_view(), name="academy-me"),
    path(
        "academy/certificates/<str:code>",
        views.CertificateCheckView.as_view(),
        name="academy-certificate",
    ),
    path(
        "academy/me/certificates/<str:code>.pdf",
        views.CertificatePdfView.as_view(),
        name="academy-certificate-pdf",
    ),
    path("academy/pass", views.PassView.as_view(), name="academy-pass"),
    path(
        "academy/pass/subscribe", views.PassSubscribeView.as_view(), name="academy-pass-subscribe"
    ),
    path("academy/pass/cancel", views.PassCancelView.as_view(), name="academy-pass-cancel"),
    # Lives.
    path("academy/lives", views.LivesView.as_view(), name="academy-lives"),
    path("academy/lives/<uuid:live_id>", views.LiveRoomView.as_view(), name="academy-live"),
    path(
        "academy/lives/<uuid:live_id>/registration",
        views.LiveRegisterView.as_view(),
        name="academy-live-registration",
    ),
    path(
        "academy/lives/<uuid:live_id>/join", views.LiveJoinView.as_view(), name="academy-live-join"
    ),
    # Trainer space.
    path("academy/studio", views.StudioView.as_view(), name="academy-studio"),
    path("academy/studio/courses", views.StudioCoursesView.as_view(), name="studio-courses"),
    path(
        "academy/studio/courses/<uuid:course_id>",
        views.StudioCourseView.as_view(),
        name="studio-course",
    ),
    path(
        "academy/studio/courses/<uuid:course_id>/submit",
        views.StudioSubmitView.as_view(),
        name="studio-submit",
    ),
    path(
        "academy/studio/courses/<uuid:course_id>/archive",
        views.StudioArchiveView.as_view(),
        name="studio-archive",
    ),
    path(
        "academy/studio/courses/<uuid:course_id>/modules",
        views.StudioModulesView.as_view(),
        name="studio-modules",
    ),
    path(
        "academy/studio/modules/<uuid:module_id>",
        views.StudioModuleView.as_view(),
        name="studio-module",
    ),
    path(
        "academy/studio/modules/<uuid:module_id>/lessons",
        views.StudioLessonsView.as_view(),
        name="studio-lessons",
    ),
    path(
        "academy/studio/modules/<uuid:module_id>/questions",
        views.StudioQuestionsView.as_view(),
        name="studio-questions",
    ),
    path(
        "academy/studio/lessons/<uuid:lesson_id>",
        views.StudioLessonView.as_view(),
        name="studio-lesson",
    ),
    path(
        "academy/studio/lessons/<uuid:lesson_id>/resources",
        views.StudioResourcesView.as_view(),
        name="studio-resources",
    ),
    path(
        "academy/studio/resources/<uuid:resource_id>",
        views.StudioResourceView.as_view(),
        name="studio-resource",
    ),
    path(
        "academy/studio/questions/<uuid:question_id>",
        views.StudioQuestionView.as_view(),
        name="studio-question",
    ),
    path("academy/studio/lives", views.StudioLivesView.as_view(), name="studio-lives"),
    path(
        "academy/studio/lives/<uuid:live_id>/cancel",
        views.StudioLiveCancelView.as_view(),
        name="studio-live-cancel",
    ),
]
