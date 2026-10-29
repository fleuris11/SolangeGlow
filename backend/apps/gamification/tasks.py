from celery import shared_task

from .services import celebrations, challenges, levels, polls, quiz, rankings, routine


@shared_task(name="apps.gamification.tasks.run_quarterly")
def run_quarterly() -> dict:
    """Every 15 minutes: routine reminders at the chosen hour, results of ended votes."""
    return {"routine": routine.send_reminders(), "polls": polls.send_results()}


@shared_task(name="apps.gamification.tasks.run_daily")
def run_daily() -> dict:
    """Every night: drafts of the coming quizzes and challenges, challenges closed, levels
    of the pros, last month's rankings, reminders of the celebrations."""
    return {
        "quizzes": quiz.prepare(),
        "challenges": challenges.prepare(),
        "closed": challenges.close_due(),
        "levels": levels.refresh_all(),
        "rankings": rankings.ensure_last_month(),
        "celebrations": celebrations.send_reminders(),
    }
