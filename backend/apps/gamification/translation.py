from modeltranslation.translator import TranslationOptions, register

from .models import Celebration, Challenge, QuizQuestion, Reward, WheelPrize


@register(Reward)
class RewardTranslationOptions(TranslationOptions):
    fields = ("title", "description")


@register(QuizQuestion)
class QuizQuestionTranslationOptions(TranslationOptions):
    fields = ("text", "choice_1", "choice_2", "choice_3", "choice_4", "explanation")


@register(Challenge)
class ChallengeTranslationOptions(TranslationOptions):
    fields = ("theme", "description")


@register(WheelPrize)
class WheelPrizeTranslationOptions(TranslationOptions):
    fields = ("label",)


@register(Celebration)
class CelebrationTranslationOptions(TranslationOptions):
    fields = ("name", "message")
