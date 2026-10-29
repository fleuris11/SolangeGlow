from django.db import models
from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.pros.models import Level as ProLevel
from apps.social.serializers import AuthorSerializer

from .models import Action, Level, PollVote, Reward, Voucher, WheelPrize

# --- Points, streak, level --------------------------------------------------------------------


class GlowStreakSerializer(serializers.Serializer):
    streak = serializers.IntegerField()
    best = serializers.IntegerField()
    today_done = serializers.BooleanField()
    bonus_every = serializers.IntegerField()
    to_bonus = serializers.IntegerField()


class GlowSummarySerializer(serializers.Serializer):
    balance = serializers.IntegerField()
    earned_total = serializers.IntegerField()
    level = serializers.ChoiceField(choices=Level.choices)
    next_level = serializers.ChoiceField(choices=Level.choices, allow_null=True)
    next_level_at = serializers.IntegerField(allow_null=True)
    multiplier = serializers.FloatField()


class GlowReferralSerializer(serializers.Serializer):
    code = serializers.CharField()
    path = serializers.CharField()
    invited = serializers.IntegerField()
    rewarded = serializers.IntegerField()
    referrer_points = serializers.IntegerField()
    referee_points = serializers.IntegerField()


class GlowScaleSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=Action.choices)
    points = serializers.IntegerField()
    per_day = serializers.IntegerField(allow_null=True)
    bonus = serializers.BooleanField()


class GlowMeSerializer(GlowSummarySerializer):
    streak = GlowStreakSerializer()
    referral = GlowReferralSerializer()
    scale = GlowScaleSerializer(many=True)
    daily_max = serializers.IntegerField()
    earned_today = serializers.IntegerField()
    games_open = serializers.BooleanField()
    wheel_open = serializers.BooleanField()


class GlowCheckInSerializer(GlowStreakSerializer):
    already = serializers.BooleanField()
    gained = serializers.IntegerField()
    bonus = serializers.IntegerField()
    balance = serializers.IntegerField()


class GlowEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    amount = serializers.IntegerField()
    action = serializers.ChoiceField(choices=Action.choices)
    note = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


# --- Rewards and vouchers ---------------------------------------------------------------------


class GlowVoucherSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    kind = serializers.ChoiceField(choices=Voucher.Kind.choices)
    origin = serializers.ChoiceField(choices=Voucher.Origin.choices)
    label = serializers.CharField()
    amount_off_minor = serializers.IntegerField()
    currency = serializers.CharField()
    expires_at = serializers.DateTimeField()
    used_at = serializers.DateTimeField(allow_null=True)


class GlowCourseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()


class GlowRewardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    kind = serializers.ChoiceField(choices=Reward.Kind.choices)
    cost_points = serializers.IntegerField()
    amount_off_minor = serializers.IntegerField()
    course = GlowCourseSerializer(allow_null=True)
    min_level = serializers.ChoiceField(choices=Level.choices)
    locked = serializers.BooleanField()
    sold_out = serializers.BooleanField()
    affordable = serializers.BooleanField()


class GlowRedeemedSerializer(serializers.Serializer):
    balance = serializers.IntegerField()
    voucher = GlowVoucherSerializer(allow_null=True)
    course = GlowCourseSerializer(allow_null=True)


# --- Quiz ------------------------------------------------------------------------------------


class DailyQuizQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    position = serializers.IntegerField()
    text = serializers.CharField()
    choices = serializers.ListField(child=serializers.CharField())
    image = MediaSerializer(allow_null=True)
    audio = MediaSerializer(allow_null=True)
    answered = serializers.IntegerField(allow_null=True)
    correct = serializers.BooleanField(allow_null=True)
    answer = serializers.IntegerField(allow_null=True)
    explanation = serializers.CharField(allow_blank=True)


class DailyQuizSerializer(serializers.Serializer):
    date = serializers.DateField()
    questions = DailyQuizQuestionSerializer(many=True)
    points_per_answer = serializers.IntegerField()
    score = serializers.IntegerField()
    answered = serializers.IntegerField()


class DailyQuizOfDaySerializer(serializers.Serializer):
    quiz = DailyQuizSerializer(allow_null=True)


class DailyQuizAnswerInputSerializer(serializers.Serializer):
    choice = serializers.IntegerField(min_value=1, max_value=4)


class DailyQuizAnswerSerializer(serializers.Serializer):
    correct = serializers.BooleanField()
    answer = serializers.IntegerField()
    explanation = serializers.CharField(allow_blank=True)
    gained = serializers.IntegerField()


# --- Wheel -----------------------------------------------------------------------------------


class WheelPrizeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    kind = serializers.ChoiceField(choices=WheelPrize.Kind.choices)
    chance = serializers.DecimalField(max_digits=4, decimal_places=1)


class WheelSpinSerializer(serializers.Serializer):
    prize_id = serializers.UUIDField(allow_null=True)
    label = serializers.CharField()
    kind = serializers.ChoiceField(choices=WheelPrize.Kind.choices)
    points = serializers.IntegerField()
    voucher = GlowVoucherSerializer(allow_null=True)


class WheelSerializer(serializers.Serializer):
    open = serializers.BooleanField()
    can_spin = serializers.BooleanField()
    prizes = WheelPrizeSerializer(many=True)
    today = WheelSpinSerializer(allow_null=True)


# --- « Help me choose » ----------------------------------------------------------------------


class PollResultSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    a = serializers.IntegerField()
    b = serializers.IntegerField()


class PollSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    caption = serializers.CharField(allow_blank=True)
    author = AuthorSerializer()
    photo_a = MediaSerializer(allow_null=True)
    photo_b = MediaSerializer(allow_null=True)
    label_a = serializers.CharField(allow_blank=True)
    label_b = serializers.CharField(allow_blank=True)
    ends_at = serializers.DateTimeField()
    ended = serializers.BooleanField()
    mine = serializers.BooleanField()
    my_vote = serializers.ChoiceField(choices=PollVote.Choice.choices, allow_null=True)
    result = PollResultSerializer(allow_null=True)


class PollListSerializer(serializers.Serializer):
    results = PollSerializer(many=True)
    durations = serializers.ListField(child=serializers.IntegerField())


class PollScope(models.TextChoices):
    VOTE = "vote", "vote"
    MINE = "mine", "mine"


class PollQuerySerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=PollScope.choices, required=False, default="vote")


class PollCreateSerializer(serializers.Serializer):
    caption = serializers.CharField(max_length=140, allow_blank=True, required=False, default="")
    photo_a = serializers.UUIDField()
    photo_b = serializers.UUIDField()
    label_a = serializers.CharField(max_length=40, allow_blank=True, required=False, default="")
    label_b = serializers.CharField(max_length=40, allow_blank=True, required=False, default="")
    hours = serializers.IntegerField()


class PollVoteSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=PollVote.Choice.choices)


# --- Photo challenge -------------------------------------------------------------------------


class ChallengeEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author = AuthorSerializer()
    photo = MediaSerializer(allow_null=True)
    caption = serializers.CharField(allow_blank=True)
    votes = serializers.IntegerField()
    voted = serializers.BooleanField()
    mine = serializers.BooleanField()


class ChallengeCurrentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    theme = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    entries = ChallengeEntrySerializer(many=True)
    my_entry = serializers.UUIDField(allow_null=True)
    votes_left = serializers.IntegerField()


class ChallengeFeaturedSerializer(serializers.Serializer):
    theme = serializers.CharField()
    ends_on = serializers.DateField()
    winner = ChallengeEntrySerializer()


class ChallengeSerializer(serializers.Serializer):
    current = ChallengeCurrentSerializer(allow_null=True)
    featured = ChallengeFeaturedSerializer(allow_null=True)


class ChallengeEnterSerializer(serializers.Serializer):
    photo_id = serializers.UUIDField()
    caption = serializers.CharField(max_length=140, allow_blank=True, required=False, default="")


# --- Rankings --------------------------------------------------------------------------------


class RankingTradeSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    icon = serializers.CharField()


class RankingRowSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    level = serializers.ChoiceField(choices=ProLevel.choices)
    verified = serializers.BooleanField()
    average = serializers.DecimalField(max_digits=3, decimal_places=2)
    reviews = serializers.IntegerField()


class RankingSerializer(serializers.Serializer):
    month = serializers.DateField(allow_null=True)
    cities = serializers.ListField(child=serializers.CharField())
    trades = RankingTradeSerializer(many=True)
    city = serializers.CharField(allow_blank=True)
    trade = serializers.CharField(allow_blank=True)
    rows = RankingRowSerializer(many=True)


class RankingQuerySerializer(serializers.Serializer):
    month = serializers.DateField(required=False)
    city = serializers.CharField(required=False, default="", allow_blank=True, max_length=80)
    trade = serializers.CharField(required=False, default="", allow_blank=True, max_length=40)


# --- Referrals -------------------------------------------------------------------------------


class InviteSerializer(serializers.Serializer):
    name = serializers.CharField()
    points = serializers.IntegerField()


class ReferralInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12)


# --- Routine and calendar --------------------------------------------------------------------


class RoutineStepSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    done = serializers.BooleanField()


class RoutineSerializer(serializers.Serializer):
    morning = RoutineStepSerializer(many=True)
    evening = RoutineStepSerializer(many=True)
    routine_reminders = serializers.BooleanField()
    morning_at = serializers.TimeField(format="%H:%M")
    evening_at = serializers.TimeField(format="%H:%M")
    celebration_reminders = serializers.BooleanField()
    max_steps = serializers.IntegerField()


class RoutineStepsInputSerializer(serializers.Serializer):
    morning = serializers.ListField(child=serializers.CharField(max_length=60), max_length=20)
    evening = serializers.ListField(child=serializers.CharField(max_length=60), max_length=20)


class RoutineCheckInputSerializer(serializers.Serializer):
    done = serializers.BooleanField()


class RemindersInputSerializer(serializers.Serializer):
    routine_reminders = serializers.BooleanField()
    morning_at = serializers.TimeField()
    evening_at = serializers.TimeField()
    celebration_reminders = serializers.BooleanField()


class CelebrationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    message = serializers.CharField(allow_blank=True)
    date = serializers.DateField()
    days_left = serializers.IntegerField()
    trade = serializers.CharField(allow_blank=True)
    search = serializers.CharField(allow_blank=True)
    gift_occasion = serializers.CharField(allow_blank=True)


class CelebrationQuerySerializer(serializers.Serializer):
    country = serializers.RegexField(r"^[A-Z]{2}$", required=False, default="")


# --- Home page -------------------------------------------------------------------------------


class TodayQuizSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    answered = serializers.IntegerField()
    score = serializers.IntegerField()


class TodayWheelSerializer(serializers.Serializer):
    open = serializers.BooleanField()
    can_spin = serializers.BooleanField()


class TodayChallengeSerializer(serializers.Serializer):
    theme = serializers.CharField()
    ends_on = serializers.DateField()
    entries = serializers.IntegerField()


class GlowTodaySerializer(serializers.Serializer):
    signed_in = serializers.BooleanField()
    games_open = serializers.BooleanField()
    summary = GlowSummarySerializer(allow_null=True)
    streak = GlowStreakSerializer(allow_null=True)
    quiz = TodayQuizSerializer(allow_null=True)
    wheel = TodayWheelSerializer(allow_null=True)
    challenge = TodayChallengeSerializer(allow_null=True)
    featured = ChallengeFeaturedSerializer(allow_null=True)
    poll = PollSerializer(allow_null=True)
    celebration = CelebrationSerializer(allow_null=True)
