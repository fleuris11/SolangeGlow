"""Writing a course: guided creation, prices, quiz, review before publication."""

import pytest

from apps.academy import errors
from apps.academy.models import Course, Enrollment
from apps.academy.services import courses
from apps.core.media.models import MediaAsset
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification

from .factories import course, setting, trainer, video

pytestmark = pytest.mark.django_db
C = Course.Status


def new_course(pro, **values):
    values.setdefault("title", "Maquillage mariée")
    return courses.create_course(pro.user, **values)


def test_a_pro_writes_a_draft_with_modules_lessons_and_a_quiz():
    pro = trainer()
    draft = new_course(pro, level="intermediate", trade="makeup", summary="Un teint qui tient")
    assert (draft.status, draft.pro, draft.currency) == (C.DRAFT, pro, "XOF")
    assert draft.slug == "maquillage-mariee"
    assert new_course(pro).slug.startswith("maquillage-mariee-")

    module = courses.save_module(draft, pro.user, title="Préparer la peau")
    lesson = courses.save_lesson(
        module, pro.user, title="Nettoyer", video_id=video(pro.user, seconds=300).pk
    )
    assert lesson.duration_seconds == 300
    draft.refresh_from_db()
    assert draft.duration_seconds == 300
    question = courses.save_question(
        module,
        pro.user,
        text="Avant le fond de teint ?",
        choices=["Hydrater", "Poudrer"],
        correct=0,
    )
    assert question.choices == ["Hydrater", "Poudrer"]

    with pytest.raises(errors.InvalidQuestion):
        courses.save_question(module, pro.user, text="Une seule ?", choices=["Oui"], correct=0)
    with pytest.raises(errors.InvalidQuestion):
        courses.save_question(module, pro.user, text="Hors liste", choices=["A", "B"], correct=2)
    with pytest.raises(errors.InvalidLesson):
        courses.save_lesson(module, pro.user, title="Sans vidéo")
    someone_else = adult("Mireille")
    with pytest.raises(errors.InvalidLesson):  # a video of somebody else
        courses.save_lesson(module, pro.user, title="Volée", video_id=video(someone_else).pk)
    with pytest.raises(errors.NotTrainer):
        courses.save_module(draft, someone_else, title="Intrusion")


def test_prices_stay_within_the_limits_and_the_pass_is_for_the_platform():
    pro = trainer()
    setting("academy.price_limits", "[1000, 20000]", "json")
    with pytest.raises(errors.InvalidPrice) as caught:
        new_course(pro, pricing="paid", price_minor=500)
    assert caught.value.details["min"].startswith("1")
    paid = new_course(pro, pricing="paid", price_minor=5000)
    assert paid.price_minor == 5000
    with pytest.raises(errors.PassOnlyForPlatform):
        new_course(pro, pricing="pass")
    free = courses.update_course(paid, pro.user, pricing="free")
    assert (free.pricing, free.price_minor) == ("free", 0)


def test_review_then_publication_or_sent_back_with_a_note():
    pro = trainer()
    draft = new_course(pro)
    with pytest.raises(errors.NotReady):
        courses.submit(draft, pro.user)
    module = courses.save_module(draft, pro.user, title="Module 1")
    waiting = video(pro.user, status=MediaAsset.Status.PROCESSING)
    courses.save_lesson(module, pro.user, title="Leçon", video_id=waiting.pk)
    with pytest.raises(errors.NotReady):  # the video is not ready yet
        courses.submit(draft, pro.user)
    waiting.status = MediaAsset.Status.READY
    waiting.variants = {"low": {"path": "video/x/low.mp4"}}
    waiting.save()

    sent = courses.submit(draft, pro.user)
    assert sent.status == C.IN_REVIEW and sent.submitted_at
    with pytest.raises(errors.NotEditable):
        courses.update_course(sent, pro.user, title="Pendant la revue")

    team = adult("Équipe", is_staff=True)
    back = courses.reject(sent, team, note="Le son de la leçon 1 est trop bas.")
    assert (back.status, back.review_note) == (C.REJECTED, "Le son de la leçon 1 est trop bas.")
    assert Notification.objects.filter(user=pro.user, event_key="academy.course_rejected").exists()

    courses.submit(back, pro.user)
    published = courses.approve(back, team)
    assert published.status == C.PUBLISHED and published.published_at
    assert Notification.objects.filter(user=pro.user, event_key="academy.course_published").exists()

    # Changed after publication: it stays online, the team looks at it again.
    courses.update_course(published, pro.user, summary="Nouveau résumé")
    published.refresh_from_db()
    assert published.status == C.PUBLISHED and published.needs_recheck
    courses.approve(published, team)
    published.refresh_from_db()
    assert not published.needs_recheck


def test_the_team_publishes_the_platform_courses_at_once():
    member = adult("Équipe", is_staff=True, is_superuser=True)
    platform = courses.create_course(
        member, platform=True, country="BJ", title="Hygiène", pricing="pass"
    )
    assert platform.pro is None and platform.pricing == "pass"
    module = courses.save_module(platform, member, title="Un poste propre")
    courses.save_lesson(module, member, title="Désinfecter", video_id=video(member).pk)
    assert courses.submit(platform, member).status == C.PUBLISHED
    with pytest.raises(errors.NotTrainer):
        courses.create_course(adult("Awa"), platform=True, country="BJ", title="Non")


def test_content_with_students_is_kept_and_an_archived_course_leaves_the_catalogue():
    pro = trainer()
    published = course(pro, modules=(("Module", 1),))
    Enrollment.objects.create(course=published, user=adult("Élève"), access="free")
    module = published.modules.first()
    with pytest.raises(errors.NotEditable):
        courses.delete_module(module, pro.user)
    with pytest.raises(errors.NotEditable):
        courses.delete_lesson(module.lessons.first(), pro.user)
    archived = courses.archive(published, pro.user)
    assert archived.status == C.ARCHIVED
    assert courses.archive(archived, pro.user).status == C.ARCHIVED


def test_a_draft_can_lose_a_module_a_lesson_a_resource_and_a_question():
    pro = trainer()
    draft = course(pro, status=C.DRAFT, modules=(("A", 2), ("B", 1)), quiz=1)
    first = draft.modules.first()
    lesson = first.lessons.first()
    pdf = MediaAsset.objects.create(
        owner=pro.user,
        kind="document",
        purpose="course_resource",
        visibility="private",
        status=MediaAsset.Status.READY,
        variants={"file": {"path": "document/x/document.pdf"}},
    )
    resource = courses.add_resource(lesson, pro.user, title="Fiche produits", file_id=pdf.pk)
    courses.delete_resource(resource, pro.user)
    courses.delete_question(first.questions.first(), pro.user)
    courses.delete_lesson(lesson, pro.user)
    courses.delete_module(draft.modules.last(), pro.user)
    draft.refresh_from_db()
    assert draft.modules.count() == 1 and draft.duration_seconds == 240
    with pytest.raises(errors.InvalidLesson):
        courses.add_resource(first.lessons.first(), pro.user, title="Sans fichier", file_id=None)
