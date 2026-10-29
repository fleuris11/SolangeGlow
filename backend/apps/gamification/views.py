from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView

from . import selectors
from . import serializers as s
from .models import Action
from .services import challenges, points, polls, quiz, referrals, rewards, routine, streaks, wheel

TAGS = ["games"]


class GameView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "games"


class PublicGameView(OptionalAuthView):
    throttle_scope = "games"


def _viewer(request):
    return request.user if request.user.is_authenticated else None


# --- Points, streak --------------------------------------------------------------------------


class MeView(GameView):
    @extend_schema(tags=TAGS, responses=s.GlowMeSerializer)
    def get(self, request):
        return Response(s.GlowMeSerializer(selectors.me(request.user)).data)


class CheckInView(GameView):
    @extend_schema(tags=TAGS, request=None, responses=s.GlowCheckInSerializer)
    def post(self, request):
        found = streaks.check_in(request.user)
        found["balance"] = points.balance(request.user)
        return Response(s.GlowCheckInSerializer(found).data)


class HistoryView(GameView):
    @extend_schema(tags=TAGS, responses=s.GlowEntrySerializer(many=True))
    def get(self, request):
        return Response(s.GlowEntrySerializer(selectors.history(request.user), many=True).data)


class TodayView(PublicGameView):
    @extend_schema(tags=TAGS, responses=s.GlowTodaySerializer)
    def get(self, request):
        return Response(s.GlowTodaySerializer(selectors.today_payload(_viewer(request))).data)


# --- Rewards ---------------------------------------------------------------------------------


class RewardsView(GameView):
    @extend_schema(tags=TAGS, responses=s.GlowRewardSerializer(many=True))
    def get(self, request):
        rows = selectors.rewards_payload(request.user)
        return Response(s.GlowRewardSerializer(rows, many=True).data)


class RedeemView(GameView):
    @extend_schema(tags=TAGS, request=None, responses=s.GlowRedeemedSerializer)
    def post(self, request, reward_id):
        found = rewards.redeem(request.user, reward_id)
        course = found["course"]
        payload = {
            "balance": points.balance(request.user),
            "voucher": selectors.voucher_payload(found["voucher"]) if found["voucher"] else None,
            "course": {"slug": course.slug, "title": course.title} if course else None,
        }
        return Response(s.GlowRedeemedSerializer(payload).data)


class VouchersView(GameView):
    @extend_schema(tags=TAGS, responses=s.GlowVoucherSerializer(many=True))
    def get(self, request):
        return Response(s.GlowVoucherSerializer(selectors.vouchers(request.user), many=True).data)


# --- Quiz ------------------------------------------------------------------------------------


class QuizView(GameView):
    @extend_schema(tags=TAGS, responses=s.DailyQuizOfDaySerializer)
    def get(self, request):
        return Response(
            s.DailyQuizOfDaySerializer({"quiz": selectors.quiz_payload(request.user)}).data
        )


class QuizAnswerView(GameView):
    @extend_schema(
        tags=TAGS, request=s.DailyQuizAnswerInputSerializer, responses=s.DailyQuizAnswerSerializer
    )
    def post(self, request, question_id):
        data = s.DailyQuizAnswerInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        found = quiz.answer(request.user, question_id, data.validated_data["choice"])
        return Response(s.DailyQuizAnswerSerializer(found).data)


# --- Wheel -----------------------------------------------------------------------------------


class WheelView(GameView):
    @extend_schema(tags=TAGS, responses=s.WheelSerializer)
    def get(self, request):
        return Response(s.WheelSerializer(selectors.wheel_payload(request.user)).data)


class SpinView(GameView):
    @extend_schema(tags=TAGS, request=None, responses=s.WheelSpinSerializer)
    def post(self, request):
        spin = wheel.spin(request.user)
        return Response(s.WheelSpinSerializer(selectors.spin_payload(spin)).data)


# --- « Help me choose » ----------------------------------------------------------------------


class PollsView(GameView):
    @extend_schema(
        tags=TAGS,
        operation_id="games_polls_list",
        parameters=[s.PollQuerySerializer],
        responses=s.PollListSerializer,
    )
    def get(self, request):
        query = s.PollQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        if query.validated_data["scope"] == "mine":
            rows = polls.visible_to(None).filter(author=request.user)
            rows = rows.order_by("-created_at")
        else:
            rows = polls.to_vote(request.user)
        payload = {
            "results": [selectors.poll_payload(p, request.user) for p in rows[:30]],
            "durations": polls.durations(),
        }
        return Response(s.PollListSerializer(payload).data)

    @extend_schema(
        tags=TAGS,
        operation_id="games_poll_create",
        request=s.PollCreateSerializer,
        responses={201: s.PollSerializer},
    )
    def post(self, request):
        data = s.PollCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        poll = polls.create(request.user, **data.validated_data)
        return Response(
            s.PollSerializer(selectors.poll_payload(poll, request.user)).data,
            status=status.HTTP_201_CREATED,
        )


class PollView(GameView):
    @extend_schema(tags=TAGS, operation_id="games_poll_detail", responses=s.PollSerializer)
    def get(self, request, poll_id):
        poll = polls.find(poll_id, request.user)
        return Response(s.PollSerializer(selectors.poll_payload(poll, request.user)).data)

    @extend_schema(tags=TAGS, responses={204: None})
    def delete(self, request, poll_id):
        polls.delete(request.user, polls.find(poll_id, request.user))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PollVoteView(GameView):
    @extend_schema(tags=TAGS, request=s.PollVoteSerializer, responses=s.PollSerializer)
    def post(self, request, poll_id):
        data = s.PollVoteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        poll = polls.vote(
            request.user, polls.find(poll_id, request.user), data.validated_data["choice"]
        )
        return Response(s.PollSerializer(selectors.poll_payload(poll, request.user)).data)


# --- Photo challenge -------------------------------------------------------------------------


class ChallengeView(PublicGameView):
    @extend_schema(tags=TAGS, responses=s.ChallengeSerializer)
    def get(self, request):
        return Response(s.ChallengeSerializer(selectors.challenge_payload(_viewer(request))).data)


class ChallengeEnterView(GameView):
    @extend_schema(
        tags=TAGS, request=s.ChallengeEnterSerializer, responses={201: s.ChallengeSerializer}
    )
    def post(self, request):
        data = s.ChallengeEnterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        challenges.enter(request.user, **data.validated_data)
        return Response(
            s.ChallengeSerializer(selectors.challenge_payload(request.user)).data,
            status=status.HTTP_201_CREATED,
        )


class ChallengeVoteView(GameView):
    @extend_schema(tags=TAGS, request=None, responses=s.ChallengeSerializer)
    def post(self, request, entry_id):
        challenges.vote(request.user, entry_id)
        return Response(s.ChallengeSerializer(selectors.challenge_payload(request.user)).data)


# --- Rankings, referrals, calendar -----------------------------------------------------------


class RankingsView(PublicGameView):
    @extend_schema(tags=TAGS, parameters=[s.RankingQuerySerializer], responses=s.RankingSerializer)
    def get(self, request):
        query = s.RankingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        payload = selectors.rankings_payload(
            month=values.get("month"), city=values["city"], trade_key=values["trade"]
        )
        return Response(s.RankingSerializer(payload).data)


class InviteView(PublicGameView):
    @extend_schema(tags=TAGS, responses=s.InviteSerializer)
    def get(self, request, code):
        referrer = referrals.referrer_of(code)
        payload = {
            "name": referrer.first_name or "",
            "points": int(points.scale().get(Action.REFERRED, 0)),
        }
        return Response(s.InviteSerializer(payload).data)


class ReferralView(GameView):
    @extend_schema(tags=TAGS, request=s.ReferralInputSerializer, responses={201: None})
    def post(self, request):
        data = s.ReferralInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        referrals.attach(request.user, data.validated_data["code"])
        return Response(status=status.HTTP_201_CREATED)


class CelebrationsView(PublicGameView):
    @extend_schema(
        tags=TAGS,
        parameters=[s.CelebrationQuerySerializer],
        responses=s.CelebrationSerializer(many=True),
    )
    def get(self, request):
        query = s.CelebrationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        rows = selectors.celebrations_payload(_viewer(request), query.validated_data["country"])
        return Response(s.CelebrationSerializer(rows, many=True).data)


# --- My routine ------------------------------------------------------------------------------


class RoutineView(GameView):
    @extend_schema(tags=TAGS, responses=s.RoutineSerializer)
    def get(self, request):
        return Response(s.RoutineSerializer(routine.state(request.user)).data)

    @extend_schema(tags=TAGS, request=s.RoutineStepsInputSerializer, responses=s.RoutineSerializer)
    def put(self, request):
        data = s.RoutineStepsInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        routine.save_steps(request.user, **data.validated_data)
        return Response(s.RoutineSerializer(routine.state(request.user)).data)


class RoutineCheckView(GameView):
    @extend_schema(tags=TAGS, request=s.RoutineCheckInputSerializer, responses=s.RoutineSerializer)
    def post(self, request, step_id):
        data = s.RoutineCheckInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        found = routine.check(request.user, step_id, done=data.validated_data["done"])
        return Response(s.RoutineSerializer(found).data)


class RemindersView(GameView):
    @extend_schema(tags=TAGS, request=s.RemindersInputSerializer, responses=s.RoutineSerializer)
    def put(self, request):
        data = s.RemindersInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        routine.set_reminders(request.user, **data.validated_data)
        return Response(s.RoutineSerializer(routine.state(request.user)).data)
