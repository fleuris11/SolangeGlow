from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class PostNotFound(DomainError):
    code = "post_not_found"
    status_code = 404
    message = _("This post does not exist or is not visible any more.")


class NotYours(DomainError):
    code = "not_yours"
    status_code = 403
    message = _("Only its author can change this.")


class InvalidMedia(DomainError):
    code = "invalid_media"
    message = _("Add the right pictures: %(rule)s")


class MediaNotReady(DomainError):
    code = "media_not_ready"
    message = _("A picture or video is still being prepared, or was refused. Wait or change it.")


class InvalidSchedule(DomainError):
    code = "invalid_schedule"
    message = _("Choose a date and time in the future, within %(days)s days.")


class InvalidLink(DomainError):
    code = "invalid_link"
    message = _("This service is not one of yours.")


class EmptyPost(DomainError):
    code = "empty_post"
    message = _("Add at least one picture or video.")


class CommentNotFound(DomainError):
    code = "comment_not_found"
    status_code = 404
    message = _("This comment does not exist any more.")


class Blocked(DomainError):
    code = "blocked"
    status_code = 403
    message = _("You cannot do this with this person.")


class CannotFollowYourself(DomainError):
    code = "cannot_follow_yourself"
    message = _("You cannot follow yourself.")


class InvalidStory(DomainError):
    code = "invalid_story"
    message = _("A story needs a picture, a video, a text or free times.")


class InvalidSlots(DomainError):
    code = "invalid_slots"
    message = _("Give the free times of today, e.g. 14:00.")


class NotAPro(DomainError):
    code = "not_a_pro"
    status_code = 403
    message = _("Only a pro can share her free slots.")


class TransactionNotFound(DomainError):
    code = "transaction_not_found"
    status_code = 404
    message = _("This booking or order does not exist.")


class NotYourTransaction(DomainError):
    code = "not_your_transaction"
    status_code = 403
    message = _("Only the person who booked or bought can leave a review.")


class NotFinished(DomainError):
    code = "not_finished"
    message = _("You can leave a review once the booking or order is finished.")


class TooLate(DomainError):
    code = "too_late"
    message = _("The time to leave a review is over (%(days)s days).")


class AlreadyReviewed(DomainError):
    code = "already_reviewed"
    message = _("You already left a review for this.")


class AlreadyReplied(DomainError):
    code = "already_replied"
    message = _("You already replied to this review.")


class ReviewNotFound(DomainError):
    code = "review_not_found"
    status_code = 404
    message = _("This review does not exist any more.")
