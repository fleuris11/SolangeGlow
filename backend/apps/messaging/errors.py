from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class ConversationNotFound(DomainError):
    code = "conversation_not_found"
    status_code = 404
    message = _("This conversation does not exist or is not yours.")


class MessageNotFound(DomainError):
    code = "message_not_found"
    status_code = 404
    message = _("This message does not exist any more.")


class CannotWriteYourself(DomainError):
    code = "cannot_write_yourself"
    message = _("You cannot write to yourself.")


class PersonNotFound(DomainError):
    code = "person_not_found"
    status_code = 404
    message = _("This person cannot be found.")


class MutualFollowNeeded(DomainError):
    code = "mutual_follow_needed"
    status_code = 403
    message = _("Two clients can write to each other once they follow each other.")


class ProtectedAccount(DomainError):
    code = "protected_account"
    status_code = 403
    message = _("This young account only gets messages from people it follows.")


class Blocked(DomainError):
    code = "blocked"
    status_code = 403
    message = _("You cannot write to this person.")


class Restricted(DomainError):
    code = "restricted"
    status_code = 403
    message = _("You cannot send messages for now, after a decision of the moderation team.")


class RequestPending(DomainError):
    code = "request_pending"
    status_code = 403
    message = _("Wait until she accepts your message request before writing again.")


class RequestDeclined(DomainError):
    code = "request_declined"
    status_code = 403
    message = _("This person does not wish to talk with you.")


class ConversationClosed(DomainError):
    code = "conversation_closed"
    status_code = 403
    message = _("This conversation is closed.")


class EmptyMessage(DomainError):
    code = "empty_message"
    message = _("Write a message, or add a picture, a voice note or a card.")


class MessageTooLong(DomainError):
    code = "message_too_long"
    message = _("This message is too long (%(max)s characters at most).")


class InvalidMedia(DomainError):
    code = "invalid_media"
    message = _("This file cannot be sent here.")


class MediaNotReady(DomainError):
    code = "media_not_ready"
    message = _("The picture or voice note is still being prepared, or was refused.")


class ShareNotFound(DomainError):
    code = "share_not_found"
    status_code = 404
    message = _("What you want to share does not exist or is not visible.")


class ShareUnavailable(DomainError):
    code = "share_unavailable"
    message = _("This kind of card cannot be shared yet.")


class NotYours(DomainError):
    code = "not_yours"
    status_code = 403
    message = _("Only its sender can delete this message.")


class TooManyQuickReplies(DomainError):
    code = "too_many_quick_replies"
    message = _("You can save %(max)s quick replies at most.")


class NotAPro(DomainError):
    code = "not_a_pro"
    status_code = 403
    message = _("Only a pro can use this.")


class TooManyMembers(DomainError):
    code = "too_many_members"
    message = _("A group can have %(max)s people at most.")


class CallsClosed(DomainError):
    code = "calls_closed"
    status_code = 403
    message = _("Calls are not open in your country yet.")


class CannotCall(DomainError):
    code = "cannot_call"
    status_code = 403
    message = _("Calls are possible between two people, or in a dispute room.")


class CallNeedsAcceptedChat(DomainError):
    code = "call_needs_accepted_chat"
    status_code = 403
    message = _("You can call once she has accepted your messages.")


class DoesNotTakeCalls(DomainError):
    code = "does_not_take_calls"
    status_code = 403
    message = _("This person does not take calls. Write her a message.")


class CallsUnavailable(DomainError):
    code = "calls_unavailable"
    status_code = 503
    message = _("Calls are not available right now. Try again in a few minutes.")


class CallNotFound(DomainError):
    code = "call_not_found"
    status_code = 404
    message = _("This call does not exist or is not yours.")


class CallOver(DomainError):
    code = "call_over"
    message = _("This call is over.")


class CallFull(DomainError):
    code = "call_full"
    status_code = 409
    message = _("This call already has %(max)s people.")
