"""Demo of the games (seed_demo): quizzes approved for the week, this week's photo
challenge and last week's winner, « Help me choose » votes, Awa's points (Star level, a
streak of 5 days), her routine, a referral, the levels of the pros and the rankings."""

from __future__ import annotations

import datetime

from django.utils import timezone, translation

from apps.academy.models import Course
from apps.accounts.models import User
from apps.pros.models import Level as ProLevel
from apps.pros.models import ProProfile
from apps.social.demo import _picture

from .models import (
    Action,
    Challenge,
    ChallengeEntry,
    ChallengeVote,
    GlowProfile,
    Poll,
    PollVote,
    QuizDay,
    QuizQuestion,
    Referral,
    Reward,
)
from .services import challenges, levels, points, rankings, routine, streaks
from .services.common import profile_of

AWA, FIFAME, INES, GRACE = (
    "+2290197000201",
    "+2290196000202",
    "ines.durand@example.com",
    "+33612340204",
)

# (fr, en) question, three answers, the right one, explanation
QUESTIONS = [
    (
        (
            "Quel beurre vient d'un arbre du nord du Bénin ?",
            "Which butter comes from a tree of northern Benin?",
        ),
        (("Le karité", "Shea"), ("Le cacao", "Cocoa"), ("L'argan", "Argan")),
        1,
        ("Le karité nourrit la peau et les cheveux.", "Shea feeds skin and hair."),
        "skincare",
    ),
    (
        (
            "Toutes les combien remettre de la crème solaire ?",
            "How often should you put sunscreen again?",
        ),
        (
            ("30 minutes", "30 minutes"),
            ("2 heures", "2 hours"),
            ("Une fois par jour", "Once a day"),
        ),
        2,
        ("Toutes les 2 heures, et après la baignade.", "Every 2 hours, and after swimming."),
        "skincare",
    ),
    (
        ("Combien de temps garder des tresses au plus ?", "How long can you keep braids at most?"),
        (("2 semaines", "2 weeks"), ("6 à 8 semaines", "6 to 8 weeks"), ("6 mois", "6 months")),
        2,
        ("Au-delà de 8 semaines, les racines s'abîment.", "After 8 weeks, the roots get damaged."),
        "braids",
    ),
    (
        ("Le premier geste avant le maquillage ?", "The first step before make-up?"),
        (
            ("Hydrater la peau", "Moisturise"),
            ("Le parfum", "Perfume"),
            ("Le rouge à lèvres", "Lipstick"),
        ),
        1,
        (
            "Une peau hydratée garde le teint toute la journée.",
            "Moisturised skin keeps the make-up all day.",
        ),
        "makeup",
    ),
    (
        ("Le savon noir est fait avec…", "Black soap is made with…"),
        (("Des cendres de plantes", "Plant ashes"), ("Du charbon", "Coal"), ("Du café", "Coffee")),
        1,
        (
            "Cendres de plantes et huiles : il nettoie en douceur.",
            "Plant ashes and oils: it cleans gently.",
        ),
        "skincare",
    ),
    (
        ("Pour un vernis qui tient plus longtemps ?", "For a nail polish that lasts longer?"),
        (
            ("Base et top coat", "Base and top coat"),
            ("Souffler dessus", "Blow on it"),
            ("Une couche épaisse", "One thick coat"),
        ),
        1,
        (
            "La base protège l'ongle, le top coat protège la couleur.",
            "The base protects the nail, the top coat the colour.",
        ),
        "nails",
    ),
    (
        ("Un foulard en soie la nuit, ça sert à… ?", "A silk scarf at night is for…?"),
        (
            ("Protéger les cheveux", "Protecting the hair"),
            ("Rien", "Nothing"),
            ("Avoir chaud", "Keeping warm"),
        ),
        1,
        (
            "La soie évite la casse et garde l'hydratation.",
            "Silk avoids breakage and keeps moisture.",
        ),
        "headwrap",
    ),
    (
        ("Le wax est un tissu…", "Wax print is a fabric…"),
        (("Imprimé à la cire", "Printed with wax"), ("Tricoté", "Knitted"), ("En cuir", "Leather")),
        1,
        (
            "La cire protège le tissu pendant la teinture.",
            "The wax protects the fabric while it is dyed.",
        ),
        "sewing",
    ),
    (
        (
            "Combien d'eau boire par jour pour une belle peau ?",
            "How much water a day for a nice skin?",
        ),
        (
            ("Environ 1,5 litre", "About 1.5 litres"),
            ("Un verre", "One glass"),
            ("5 litres", "5 litres"),
        ),
        1,
        ("L'eau aide la peau à rester souple.", "Water helps the skin stay supple."),
        "skincare",
    ),
]


def _team_owner():
    return User.objects.filter(is_staff=True).first() or User.objects.filter(phone=AWA).first()


def _quizzes(owner, today) -> int:
    pictures = {}
    made = 0
    for offset in range(-1, 7):
        day = today + datetime.timedelta(days=offset)
        if QuizDay.objects.filter(date=day).exists():
            continue
        quiz = QuizDay.objects.create(
            date=day,
            status=QuizDay.Status.APPROVED,
            generated_by="demo",
            approved_at=timezone.now(),
        )
        for position in range(3):
            text, choices, answer, explanation, trade = QUESTIONS[(offset * 3 + position + 3) % 9]
            if trade not in pictures:
                pictures[trade] = _picture(owner, f"quiz-{trade}", trade, purpose="quiz_image")
            values = {}
            for index, (fr, en) in enumerate(choices, start=1):
                values.update({f"choice_{index}_fr": fr, f"choice_{index}_en": en})
            with translation.override("fr"):
                QuizQuestion.objects.create(
                    quiz=quiz,
                    position=position,
                    text_fr=text[0],
                    text_en=text[1],
                    answer=answer,
                    explanation_fr=explanation[0],
                    explanation_en=explanation[1],
                    image=pictures[trade],
                    **values,
                )
        made += 1
    return made


def _challenges(people, today) -> int:
    monday = challenges.monday_of(today)
    if Challenge.objects.filter(starts_on=monday).exists():
        return 0
    last = Challenge.objects.create(
        theme_fr="Tresses du marché",
        theme_en="Market braids",
        description_fr="Tes plus belles tresses du samedi.",
        description_en="Your nicest Saturday braids.",
        starts_on=monday - datetime.timedelta(days=7),
        ends_on=monday - datetime.timedelta(days=1),
        status=Challenge.Status.APPROVED,
        generated_by="demo",
    )
    current = Challenge.objects.create(
        theme_fr="Look pagne du dimanche",
        theme_en="Sunday pagne look",
        description_fr="Montre ta tenue en pagne pour la messe ou la fête.",
        description_en="Show your pagne outfit for church or the party.",
        starts_on=monday,
        ends_on=monday + datetime.timedelta(days=6),
        status=Challenge.Status.APPROVED,
        generated_by="demo",
    )
    for challenge, trade, votes in ((last, "braids", [5, 3, 2]), (current, "sewing", [4, 2, 1])):
        for index, (person, count) in enumerate(zip(people[1:], votes, strict=False)):
            entry = ChallengeEntry.objects.create(
                challenge=challenge,
                author=person,
                photo=_picture(
                    person, f"challenge-{challenge.pk}-{index}", trade, purpose="challenge_photo"
                ),
                caption="",
                votes=count,
            )
            for voter in people[:count]:
                if voter != person:
                    ChallengeVote.objects.get_or_create(
                        entry=entry, challenge=challenge, user=voter
                    )
    challenges.close_due()
    return 2


def _polls(fifame, awa, others) -> int:
    if Poll.objects.exists():
        return 0
    asked = [
        (
            fifame,
            "Tresses ou locks pour le mariage de ma cousine ?",
            "Tresses",
            "Locks",
            "braids",
            "hair",
        ),
        (awa, "Quel foulard pour samedi ?", "Rouge", "Doré", "headwrap", "headwrap"),
    ]
    for author, caption, label_a, label_b, first, second in asked:
        poll = Poll.objects.create(
            author=author,
            caption=caption,
            label_a=label_a,
            label_b=label_b,
            photo_a=_picture(author, f"poll-{caption}-a", first, purpose="poll_photo"),
            photo_b=_picture(
                author, f"poll-{caption}-b", second, stage="before", purpose="poll_photo"
            ),
            ends_at=timezone.now() + datetime.timedelta(hours=20),
            city=author.city,
        )
        for index, voter in enumerate(v for v in others if v not in (author, awa)):
            choice = "a" if index % 3 else "b"
            PollVote.objects.create(poll=poll, user=voter, choice=choice)
            field = "votes_a" if choice == "a" else "votes_b"
            setattr(poll, field, getattr(poll, field) + 1)
        poll.save()
    return len(asked)


def _awa_points(awa) -> None:
    if GlowProfile.objects.filter(user=awa, earned_total__gt=0).exists():
        return
    now = timezone.now()
    for days in range(24, 4, -1):
        moment = now - datetime.timedelta(days=days)
        for action in (Action.POST, Action.BOOKING, Action.PURCHASE):
            points.award(awa, action, key=f"demo:{action}:{days}", now=moment)
    for days in range(4, 0, -1):
        streaks.check_in(awa, now=now - datetime.timedelta(days=days))
    routine.save_steps(
        awa,
        morning=["Nettoyer mon visage", "Sérum vitamine C", "Crème solaire"],
        evening=["Démaquiller", "Beurre de karité"],
    )


def seed_games() -> dict:
    awa = User.objects.filter(phone=AWA).first()
    fifame = User.objects.filter(phone=FIFAME).first()
    if awa is None or fifame is None:
        return {"quizzes": 0, "challenges": 0, "polls": 0}
    today = timezone.localdate()
    others = list(
        User.objects.filter(pro_profile__status=ProProfile.Status.PUBLISHED).order_by("phone")[:6]
    )
    people = [awa, fifame, *others]
    made = {
        "quizzes": _quizzes(_team_owner(), today),
        "challenges": _challenges(people, today),
        "polls": _polls(fifame, awa, people),
    }
    _awa_points(awa)
    profile_of(fifame)
    if not Referral.objects.filter(referee=fifame).exists():
        Referral.objects.create(referrer=awa, referee=fifame, rewarded_at=timezone.now())
    course = Course.objects.filter(pro__isnull=True, status=Course.Status.PUBLISHED).first()
    if course is not None and not Reward.objects.filter(kind=Reward.Kind.COURSE).exists():
        Reward.objects.create(
            title_fr=f"Formation offerte : {course.title}"[:80],
            title_en=f"Free course: {course.title}"[:80],
            kind=Reward.Kind.COURSE,
            cost_points=1500,
            course=course,
            position=10,
        )
    levels.refresh_all()
    # Demo showcases have little real activity: two levels shown so that the badges can
    # be seen (the nightly task computes them again from the real activity).
    ProProfile.objects.filter(user__phone="+2290197000101").update(level=ProLevel.TOP)
    second = (
        ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED)
        .exclude(user__phone="+2290197000101")
        .order_by("-rating_count", "slug")
        .first()
    )
    if second is not None:
        ProProfile.objects.filter(pk=second.pk).update(level=ProLevel.CONFIRMED)
    # The rankings of the current month, so that the page shows something in the demo
    # (in production only finished months are computed).
    rankings.compute(today)
    return made
