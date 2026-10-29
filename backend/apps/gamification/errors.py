from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class GamesUnavailable(DomainError):
    code = "games_unavailable"
    message = _("The games are not open in your country yet.")


class WheelUnavailable(DomainError):
    code = "wheel_unavailable"
    message = _("The Glow wheel is not open in your country yet.")


class NotEnoughPoints(DomainError):
    code = "not_enough_points"
    message = _("You have %(balance)s points. This needs %(cost)s.")


class RewardNotFound(DomainError):
    code = "reward_not_found"
    status_code = 404
    message = _("This reward does not exist or is no longer offered.")


class RewardLocked(DomainError):
    code = "reward_locked"
    message = _("This reward opens at the %(level)s level.")


class RewardSoldOut(DomainError):
    code = "reward_sold_out"
    message = _("This reward is sold out. Come back soon.")


class RewardNotHere(DomainError):
    code = "reward_not_here"
    message = _("This reward is not offered in your country.")


class CannotBuy(DomainError):
    code = "glow_cannot_buy"
    status_code = 403
    message = _("You must be an adult to use a discount.")


class VoucherNotFound(DomainError):
    code = "voucher_not_found"
    message = _("This voucher does not exist, was used or is over.")


class VoucherNotForThis(DomainError):
    code = "voucher_not_for_this"
    message = _("This voucher cannot be used on this order.")


class AlreadyAnswered(DomainError):
    code = "quiz_already_answered"
    message = _("You already answered this question.")


class QuestionNotFound(DomainError):
    code = "quiz_question_not_found"
    status_code = 404
    message = _("This question is not in today's quiz.")


class InvalidChoice(DomainError):
    code = "glow_invalid_choice"
    message = _("Choose one of the answers shown.")


class QuizIncomplete(DomainError):
    code = "quiz_incomplete"
    message = _("The quiz needs %(count)s complete questions before it is approved.")


class AlreadySpun(DomainError):
    code = "wheel_already_spun"
    message = _("You already spun the wheel today. Come back tomorrow!")


class NoPrize(DomainError):
    code = "wheel_no_prize"
    message = _("The wheel is being prepared. Come back later.")


class PollNotFound(DomainError):
    code = "poll_not_found"
    status_code = 404
    message = _("This vote does not exist or is over.")


class PollClosed(DomainError):
    code = "poll_closed"
    message = _("This vote is over. See the result.")


class OwnPoll(DomainError):
    code = "poll_own"
    message = _("You cannot vote on your own question.")


class AlreadyVoted(DomainError):
    code = "glow_already_voted"
    message = _("You already voted.")


class InvalidPhotos(DomainError):
    code = "glow_invalid_photos"
    message = _("Add two photos that you took.")


class InvalidDuration(DomainError):
    code = "poll_invalid_duration"
    message = _("Choose one of the durations shown.")


class TooManyPolls(DomainError):
    code = "poll_too_many"
    message = _("You already have %(count)s open questions. Wait for a result.")


class CannotPost(DomainError):
    code = "glow_cannot_post"
    status_code = 403
    message = _("You cannot publish for now.")


class NoChallenge(DomainError):
    code = "challenge_none"
    status_code = 404
    message = _("No photo challenge this week. Come back on Monday!")


class AlreadyEntered(DomainError):
    code = "challenge_already_entered"
    message = _("You already take part in this challenge.")


class EntryNotFound(DomainError):
    code = "challenge_entry_not_found"
    status_code = 404
    message = _("This photo is not in the challenge.")


class OwnEntry(DomainError):
    code = "challenge_own_entry"
    message = _("You cannot vote for your own photo.")


class NoVotesLeft(DomainError):
    code = "challenge_no_votes_left"
    message = _("You used your %(count)s votes for this challenge.")


class ChallengeIncomplete(DomainError):
    code = "challenge_incomplete"
    message = _("Write the theme before approving the challenge.")


class InvalidReferral(DomainError):
    code = "referral_invalid"
    message = _("This invitation link does not work.")


class ReferralTooLate(DomainError):
    code = "referral_too_late"
    message = _("An invitation is accepted only in the first %(days)s days of an account.")


class AlreadyReferred(DomainError):
    code = "referral_already"
    message = _("Your account is already linked to a godmother.")


class OwnReferral(DomainError):
    code = "referral_own"
    message = _("You cannot invite yourself.")


class StepNotFound(DomainError):
    code = "routine_step_not_found"
    status_code = 404
    message = _("This step is not in your routine.")


class TooManySteps(DomainError):
    code = "routine_too_many"
    message = _("At most %(count)s steps per moment.")
