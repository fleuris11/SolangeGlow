from django.urls import path

from . import views

urlpatterns = [
    path("glow/me", views.MeView.as_view(), name="glow-me"),
    path("glow/check-in", views.CheckInView.as_view(), name="glow-check-in"),
    path("glow/history", views.HistoryView.as_view(), name="glow-history"),
    path("glow/today", views.TodayView.as_view(), name="glow-today"),
    path("glow/rewards", views.RewardsView.as_view(), name="glow-rewards"),
    path("glow/rewards/<uuid:reward_id>/redeem", views.RedeemView.as_view(), name="glow-redeem"),
    path("glow/vouchers", views.VouchersView.as_view(), name="glow-vouchers"),
    path("glow/quiz", views.QuizView.as_view(), name="glow-quiz"),
    path(
        "glow/quiz/<uuid:question_id>/answer",
        views.QuizAnswerView.as_view(),
        name="glow-quiz-answer",
    ),
    path("glow/wheel", views.WheelView.as_view(), name="glow-wheel"),
    path("glow/wheel/spin", views.SpinView.as_view(), name="glow-wheel-spin"),
    path("glow/polls", views.PollsView.as_view(), name="glow-polls"),
    path("glow/polls/<uuid:poll_id>", views.PollView.as_view(), name="glow-poll"),
    path("glow/polls/<uuid:poll_id>/vote", views.PollVoteView.as_view(), name="glow-poll-vote"),
    path("glow/challenge", views.ChallengeView.as_view(), name="glow-challenge"),
    path("glow/challenge/entries", views.ChallengeEnterView.as_view(), name="glow-challenge-enter"),
    path(
        "glow/challenge/entries/<uuid:entry_id>/vote",
        views.ChallengeVoteView.as_view(),
        name="glow-challenge-vote",
    ),
    path("glow/rankings", views.RankingsView.as_view(), name="glow-rankings"),
    path("glow/invite/<str:code>", views.InviteView.as_view(), name="glow-invite"),
    path("glow/referral", views.ReferralView.as_view(), name="glow-referral"),
    path("glow/celebrations", views.CelebrationsView.as_view(), name="glow-celebrations"),
    path("glow/routine", views.RoutineView.as_view(), name="glow-routine"),
    path(
        "glow/routine/<uuid:step_id>", views.RoutineCheckView.as_view(), name="glow-routine-check"
    ),
    path("glow/reminders", views.RemindersView.as_view(), name="glow-reminders"),
]
