from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class AcademyClosed(DomainError):
    code = "academy_closed"
    status_code = 404
    message = _("The academy is not open in your country yet.")


class LivesClosed(DomainError):
    code = "lives_closed"
    status_code = 404
    message = _("Training lives are not open in your country yet.")


class CourseNotFound(DomainError):
    code = "course_not_found"
    status_code = 404
    message = _("This course does not exist or is not available.")


class NotTrainer(DomainError):
    code = "not_trainer"
    status_code = 403
    message = _("Only the trainer of this course can change it.")


class InvalidCourse(DomainError):
    code = "invalid_course"
    message = _("Check the title, the level, the language and the trade.")


class InvalidPrice(DomainError):
    code = "invalid_price"
    message = _("Choose a price between %(min)s and %(max)s.")


class PassOnlyForPlatform(DomainError):
    code = "pass_only_for_platform"
    message = _("Only the courses of Solange Glow are included in the pass for now.")


class NotEditable(DomainError):
    code = "course_not_editable"
    message = _("This course is being reviewed: wait for the answer before changing it.")


class NotReady(DomainError):
    code = "course_not_ready"
    message = _(
        "Before sending it: a title, at least one module with a lesson, and every video ready."
    )


class InvalidLesson(DomainError):
    code = "invalid_lesson"
    message = _("Give a title and a video of 3 to 10 minutes.")


class InvalidQuestion(DomainError):
    code = "invalid_question"
    message = _("Write the question, 2 to 4 answers, and tick the right one.")


class InvalidTransition(DomainError):
    code = "invalid_course_transition"
    message = _("This course cannot do that now.")


class WaiverRequired(DomainError):
    code = "waiver_required"
    message = _("Tick the box to start right away: it is needed to open the course at once.")


class CannotBuy(DomainError):
    code = "cannot_buy"
    status_code = 403
    message = _("Buying is not open to your account. Free courses stay open to you.")


class AlreadyEnrolled(DomainError):
    code = "already_enrolled"
    message = _("You already follow this course.")


class NotEnrolled(DomainError):
    code = "not_enrolled"
    status_code = 403
    message = _("Get this course to watch this lesson.")


class PassRequired(DomainError):
    code = "pass_required"
    status_code = 403
    message = _("This course is included in the pass: take the pass to follow it.")


class RefundClosed(DomainError):
    code = "refund_closed"
    message = _("A refund is only possible within %(days)s days and before opening a lesson.")


class QuizLocked(DomainError):
    code = "quiz_locked"
    message = _("Watch every lesson of the module first.")


class InvalidAnswers(DomainError):
    code = "invalid_answers"
    message = _("Answer every question.")


class PassNotOffered(DomainError):
    code = "pass_not_offered"
    status_code = 404
    message = _("The pass is not offered in your country yet.")


class PassActive(DomainError):
    code = "pass_active"
    message = _("Your pass is already paid for this month.")


class NothingToPay(DomainError):
    code = "nothing_to_pay"
    message = _("There is nothing to pay right now.")


class InvalidLive(DomainError):
    code = "invalid_live"
    message = _("Give a title, a date in the future, a length and a number of places.")


class LiveNotFound(DomainError):
    code = "live_not_found"
    status_code = 404
    message = _("This live does not exist or is over.")


class LiveFull(DomainError):
    code = "live_full"
    message = _("No place left in this live.")


class LiveNotOpen(DomainError):
    code = "live_not_open"
    message = _("The room opens %(minutes)s minutes before the start.")


class BroadcastNotAvailable(DomainError):
    code = "broadcast_not_available"
    status_code = 503
    message = _("The live video is not available yet: it is coming soon.")


class CertificateNotFound(DomainError):
    code = "certificate_not_found"
    status_code = 404
    message = _("No certificate with this code.")
