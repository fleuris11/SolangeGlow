"""The playful side in the back office: the points ledger (read only, corrections as new
entries), the rewards, the wheel and its chances, quizzes and challenges approved in one
click, « Help me choose » votes, rankings, referrals and the calendar of celebrations."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from unfold.admin import StackedInline, TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.media.services import create_asset, variant_url
from apps.core.money import Money
from apps.moderation.services import set_visibility

from .models import (
    Celebration,
    Challenge,
    ChallengeEntry,
    GlowProfile,
    PointsEntry,
    Poll,
    QuizDay,
    QuizQuestion,
    Ranking,
    Referral,
    Reward,
    Voucher,
    WheelPrize,
    WheelSpin,
)
from .services import challenges, points, quiz, rankings


class ReadOnlyAdmin(AuditedModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _thumb(asset, size=80):
    url = variant_url(asset, "thumb") if asset is not None else None
    return format_html('<img src="{}" width="{}" alt="">', url, size) if url else "—"


# --- Points ----------------------------------------------------------------------------------


@admin.register(PointsEntry)
class PointsEntryAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "user", "amount", "action", "day", "note", "actor"]
    list_filter = ["action", "day"]
    search_fields = ["user__email", "user__phone", "user__first_name", "key"]
    date_hierarchy = "created_at"
    list_select_related = ["user", "actor"]


class AdjustForm(forms.Form):
    amount = forms.IntegerField(
        label=_("Points"), help_text=_("Positive to give, negative to take back.")
    )
    note = forms.CharField(label=_("Reason"), max_length=200)


@admin.register(GlowProfile)
class GlowProfileAdmin(AuditedModelAdmin):
    list_display = [
        "user",
        "level",
        "show_balance",
        "earned_total",
        "streak",
        "best_streak",
        "last_checkin_on",
    ]
    list_filter = ["level", "routine_reminders", "celebration_reminders"]
    search_fields = ["user__email", "user__phone", "user__first_name", "referral_code"]
    list_select_related = ["user"]
    readonly_fields = [
        "user",
        "show_balance",
        "earned_total",
        "level",
        "streak",
        "best_streak",
        "last_checkin_on",
        "referral_code",
    ]
    fields = [
        *readonly_fields,
        "routine_reminders",
        "morning_at",
        "evening_at",
        "celebration_reminders",
    ]
    actions_detail = ["adjust_detail"]

    def has_add_permission(self, request):
        return False

    @display(description=_("balance"))
    def show_balance(self, profile):
        return points.balance(profile.user)

    @action(description=_("Give or take back points"), url_path="adjust", icon="add_circle")
    def adjust_detail(self, request, object_id):
        profile = get_object_or_404(GlowProfile, pk=object_id)
        form = AdjustForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                points.adjust(
                    profile.user,
                    form.cleaned_data["amount"],
                    note=form.cleaned_data["note"],
                    actor=request.user,
                )
            except DomainError as exc:
                self.message_user(request, exc.text(), messages.ERROR)
            else:
                self.message_user(request, _("Points written in the ledger."), messages.SUCCESS)
                return redirect(reverse("admin:gamification_glowprofile_change", args=[object_id]))
        context = {
            **self.admin_site.each_context(request),
            "title": _("Points of %(person)s") % {"person": profile.user},
            "opts": self.model._meta,
            "form": form,
            "profile": profile,
            "balance": points.balance(profile.user),
        }
        return TemplateResponse(request, "admin/gamification/adjust.html", context)


# --- Rewards and vouchers --------------------------------------------------------------------


@admin.register(Reward)
class RewardAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["title", "kind", "cost_points", "min_level", "stock", "is_active", "position"]
    list_filter = ["kind", "min_level", "is_active"]
    list_editable = ["is_active", "position"]
    search_fields = ["title"]
    autocomplete_fields = ["course"]


@admin.register(Voucher)
class VoucherAdmin(ReadOnlyAdmin):
    list_display = ["code", "user", "label", "origin", "expires_at", "used_at"]
    list_filter = ["kind", "origin"]
    search_fields = ["code", "user__email", "user__phone"]
    list_select_related = ["user"]


# --- Wheel -----------------------------------------------------------------------------------


@admin.register(WheelPrize)
class WheelPrizeAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = [
        "label",
        "kind",
        "points",
        "show_amount",
        "weight",
        "chance",
        "daily_stock",
        "countries",
        "is_active",
    ]
    list_editable = ["weight", "is_active"]
    list_filter = ["kind", "is_active"]

    def changelist_view(self, request, extra_context=None):
        messages.info(
            request,
            _(
                "One free spin a day, never paid, no purchase needed. Chance of a prize = its "
                "weight divided by the weights of the prizes available to the person."
            ),
        )
        return super().changelist_view(request, extra_context)

    @display(description=_("discount"))
    def show_amount(self, prize):
        return Money(prize.amount_off_minor, "XOF").format("fr") if prize.amount_off_minor else "—"

    @display(description=_("chance (everywhere)"))
    def chance(self, prize):
        total = (
            WheelPrize.objects.filter(is_active=True).aggregate(total=Sum("weight"))["total"] or 0
        )
        if not prize.is_active or not total:
            return "—"
        return f"{prize.weight * 100 / total:.1f} %"


@admin.register(WheelSpin)
class WheelSpinAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "user", "label", "kind", "points", "voucher"]
    list_filter = ["kind", "day"]
    search_fields = ["user__email", "user__phone"]
    list_select_related = ["user", "voucher"]


# --- Quiz ------------------------------------------------------------------------------------


class QuestionForm(forms.ModelForm):
    image_upload = forms.ImageField(label=_("new picture"), required=False)
    audio_upload = forms.FileField(label=_("new audio"), required=False)

    class Meta:
        model = QuizQuestion
        fields = [
            "position",
            "text",
            "choice_1",
            "choice_2",
            "choice_3",
            "choice_4",
            "answer",
            "explanation",
        ]


class QuestionInline(StackedInline, TranslationStackedInline):
    model = QuizQuestion
    form = QuestionForm
    extra = 0
    readonly_fields = ["preview"]

    def get_extra(self, request, obj=None, **kwargs):
        # A new quiz opens with its empty questions, ready to be written.
        return quiz.size() if obj is None or not obj.questions.exists() else 0

    @display(description=_("picture"))
    def preview(self, question):
        return _thumb(question.image) if question.pk else "—"


@admin.register(QuizDay)
class QuizDayAdmin(AuditedModelAdmin):
    list_display = ["date", "status", "questions_count", "generated_by", "approved_by"]
    list_filter = ["status", "generated_by"]
    date_hierarchy = "date"
    readonly_fields = ["status", "generated_by", "approved_at", "approved_by"]
    inlines = [QuestionInline]
    actions = ["approve"]
    actions_detail = ["approve_detail"]

    @display(description=_("questions"))
    def questions_count(self, quiz_day):
        return quiz_day.questions.count()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        uploads = {}
        for question_form in formset.forms:
            data = getattr(question_form, "cleaned_data", None) or {}
            uploads[id(question_form.instance)] = (
                data.get("image_upload"),
                data.get("audio_upload"),
            )
        for instance in instances:
            image, audio = uploads.get(id(instance), (None, None))
            if image:
                instance.image = create_asset(
                    owner=request.user, uploaded=image, purpose="quiz_image", kind="image"
                )
            if audio:
                instance.audio = create_asset(
                    owner=request.user, uploaded=audio, purpose="quiz_audio", kind="audio"
                )
            instance.save()
        for deleted in formset.deleted_objects:
            deleted.delete()

    def _approve(self, request, quiz_day) -> bool:
        try:
            quiz.approve(quiz_day, actor=request.user)
        except DomainError as exc:
            self.message_user(request, f"{quiz_day.date}: {exc.text()}", messages.ERROR)
            return False
        return True

    @admin.action(description=_("Approve"))
    def approve(self, request, queryset):
        done = sum(self._approve(request, q) for q in queryset)
        self.message_user(request, _("%(count)s quizzes approved.") % {"count": done})

    @action(description=_("Approve"), url_path="approve", icon="check_circle")
    def approve_detail(self, request, object_id):
        if self._approve(request, get_object_or_404(QuizDay, pk=object_id)):
            self.message_user(request, _("Quiz approved: it goes online on its day."))
        return redirect(reverse("admin:gamification_quizday_change", args=[object_id]))


# --- Photo challenge -------------------------------------------------------------------------


class EntryInline(TabularInline):
    model = ChallengeEntry
    extra = 0
    tab = True
    fields = ["preview", "author", "caption", "votes", "visibility"]
    readonly_fields = ["preview", "author", "caption", "votes"]

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("photo"))
    def preview(self, entry):
        return _thumb(entry.photo)


@admin.register(Challenge)
class ChallengeAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["theme", "starts_on", "ends_on", "status", "entries_count", "winner"]
    list_filter = ["status"]
    readonly_fields = ["status", "generated_by", "winner", "closed_at"]
    inlines = [EntryInline]
    actions = ["approve"]
    actions_detail = ["approve_detail"]

    @display(description=_("photos"))
    def entries_count(self, challenge):
        return challenge.entries.count()

    def _approve(self, request, challenge) -> bool:
        try:
            challenges.approve(challenge, actor=request.user)
        except DomainError as exc:
            self.message_user(request, f"{challenge.starts_on}: {exc.text()}", messages.ERROR)
            return False
        return True

    @admin.action(description=_("Approve"))
    def approve(self, request, queryset):
        done = sum(
            self._approve(request, c) for c in queryset.filter(status=Challenge.Status.DRAFT)
        )
        self.message_user(request, _("%(count)s challenges approved.") % {"count": done})

    @action(description=_("Approve"), url_path="approve", icon="check_circle")
    def approve_detail(self, request, object_id):
        if self._approve(request, get_object_or_404(Challenge, pk=object_id)):
            self.message_user(request, _("Challenge approved: it opens on its Monday."))
        return redirect(reverse("admin:gamification_challenge_change", args=[object_id]))


# --- « Help me choose » ----------------------------------------------------------------------


@admin.register(Poll)
class PollAdmin(AuditedModelAdmin):
    list_display = ["caption", "author", "photos", "votes_a", "votes_b", "ends_at", "visibility"]
    list_filter = ["visibility"]
    search_fields = ["caption", "author__email", "author__first_name"]
    list_select_related = ["author", "photo_a", "photo_b"]
    readonly_fields = [
        "author",
        "caption",
        "label_a",
        "label_b",
        "photos",
        "votes_a",
        "votes_b",
        "ends_at",
        "city",
        "result_sent_at",
        "deleted_at",
    ]
    fields = [*readonly_fields, "visibility"]
    actions = ["remove"]

    def has_add_permission(self, request):
        return False

    @display(description=_("photos"))
    def photos(self, poll):
        return format_html("{} {}", _thumb(poll.photo_a, 60), _thumb(poll.photo_b, 60))

    @admin.action(description=_("Remove from the app"))
    def remove(self, request, queryset):
        for poll in queryset:
            set_visibility(poll, "removed")
        self.message_user(request, _("Removed."))


# --- Rankings, referrals, calendar -----------------------------------------------------------


@admin.register(Ranking)
class RankingAdmin(ReadOnlyAdmin):
    list_display = ["month", "city", "trade", "position", "pro", "average", "reviews", "score"]
    list_filter = ["month", "trade", "city"]
    search_fields = ["pro__business_name", "city"]
    list_select_related = ["trade", "pro"]
    actions = ["recompute"]

    @admin.action(description=_("Compute again the months selected"))
    def recompute(self, request, queryset):
        months = sorted(set(queryset.values_list("month", flat=True)))
        for month in months:
            rankings.compute(month)
        self.message_user(request, _("%(count)s months computed.") % {"count": len(months)})


@admin.register(Referral)
class ReferralAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "referrer", "referee", "rewarded_at", "capped"]
    list_filter = ["capped"]
    search_fields = ["referrer__email", "referee__email", "referrer__phone", "referee__phone"]
    list_select_related = ["referrer", "referee"]


@admin.register(Celebration)
class CelebrationAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "date", "yearly", "countries", "remind_days", "trade", "is_active"]
    list_filter = ["yearly", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name"]
    readonly_fields = ["reminded_for"]
