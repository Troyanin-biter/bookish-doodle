# services/analytics.py
from datetime import datetime, timedelta, date
from db.database import db


DAY_NAMES = {
    "0": "Воскресенье", "1": "Понедельник", "2": "Вторник",
    "3": "Среда",       "4": "Четверг",     "5": "Пятница",
    "6": "Суббота",
}


async def calculate_streak(user_id: int) -> int:
    """Считает текущую серию (streak) выполнения задач подряд."""
    raw_dates = await db.get_completion_dates(user_id, days=365)
    if not raw_dates:
        return 0

    dates = sorted(
        [datetime.strptime(d, "%Y-%m-%d").date() if isinstance(d, str) else d
         for d in raw_dates],
        reverse=True,
    )

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Серия должна включать сегодня или хотя бы вчера
    if dates[0] != today and dates[0] != yesterday:
        return 0

    streak = 1
    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


async def daily_report(user_id: int) -> dict:
    return {
        "completed_today": await db.get_completed_today(user_id),
        "created_today":   await db.get_created_today(user_id),
        "active_tasks":    await db.get_active_tasks(user_id),
        "pending":         len(await db.get_active_tasks(user_id)),
        "streak":          await calculate_streak(user_id),
    }


async def weekly_report(user_id: int) -> dict:
    stats = await db.get_stats_period(user_id, days=7)
    daily = await db.get_daily_completions(user_id, days=7)

    best = DAY_NAMES.get(stats["by_day_of_week"][0][0]) if stats["by_day_of_week"] else None
    worst = DAY_NAMES.get(stats["by_day_of_week"][-1][0]) if stats["by_day_of_week"] else None

    return {
        **stats,
        "streak": await calculate_streak(user_id),
        "best_day": best,
        "worst_day": worst if worst != best else None,
        "daily_completions": daily,
    }


async def full_stats(user_id: int) -> dict:
    total   = await db.get_total_stats(user_id)
    monthly = await db.get_stats_period(user_id, days=30)
    wk      = await db.get_stats_period(user_id, days=7)
    best_d  = DAY_NAMES.get(monthly["by_day_of_week"][0][0]) if monthly["by_day_of_week"] else None

    return {
        "total":    total,
        "streak":   await calculate_streak(user_id),
        "weekly":   wk,
        "monthly":  monthly,
        "best_day": best_d,
    }