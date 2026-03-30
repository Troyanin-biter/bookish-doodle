import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from db.database import db
from services.analytics import daily_report
from services.comfort import sweet_ping
from services.motivation import Motivation

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _morning(bot: Bot):
    for user in await db.get_all_users():
        try:
            rpt = await daily_report(user["user_id"])
            txt = Motivation.morning() + "\n\n"

            if rpt["pending"]:
                txt += (
                    f"📋 У тебя <b>{rpt['pending']}</b> активных задач.\n"
                    "Начнем день с одной главной?\n\n"
                    "👉 /tasks"
                )
            else:
                txt += "Пока активных задач нет. Добавь новую через /add 💪"

            if rpt["streak"] > 1:
                txt += f"\n\n🔥 Серия: <b>{rpt['streak']}</b> дн."

            await bot.send_message(user["user_id"], txt, parse_mode="HTML")
        except Exception as e:
            log.debug("morning skip %s: %s", user["user_id"], e)


async def _evening(bot: Bot):
    for user in await db.get_all_users():
        try:
            rpt = await daily_report(user["user_id"])
            good = rpt["completed_today"] > 0
            txt = Motivation.evening(good) + "\n\n"
            txt += (
                "📊 <b>Итоги дня:</b>\n"
                f"✅ Выполнено: {rpt['completed_today']}\n"
                f"📋 Осталось: {rpt['pending']}"
            )

            if rpt["streak"] > 1:
                txt += f"\n🔥 Серия: {rpt['streak']} дн."

            await bot.send_message(user["user_id"], txt, parse_mode="HTML")
        except Exception as e:
            log.debug("evening skip %s: %s", user["user_id"], e)


async def _kick(bot: Bot):
    users_24 = await db.get_inactive_users(hours=24)
    users_72 = {u["user_id"] for u in await db.get_inactive_users(hours=72)}

    for user in users_24:
        try:
            days = 3 if user["user_id"] in users_72 else 1
            pending = await db.get_active_tasks(user["user_id"])
            if not pending:
                continue

            txt = Motivation.reminder(days)
            txt += f"\n\n📋 Незавершенных задач: <b>{len(pending)}</b>\n👉 /tasks"
            await bot.send_message(user["user_id"], txt, parse_mode="HTML")
        except Exception as e:
            log.debug("kick skip %s: %s", user["user_id"], e)


async def _sweet_motivation(bot: Bot):
    for user in await db.get_all_users():
        try:
            txt = (
                f"💖 <i>{sweet_ping()}</i>\n\n"
                "Если хочешь поддержку прямо сейчас: /motivation"
            )
            await bot.send_message(user["user_id"], txt, parse_mode="HTML")
        except Exception as e:
            log.debug("sweet motivation skip %s: %s", user["user_id"], e)


async def _reflection_prompt(bot: Bot):
    for user in await db.get_all_users():
        try:
            rpt = await daily_report(user["user_id"])
            if rpt["completed_today"] > 0:
                txt = (
                    "📖 Маленький вечерний ритуал:\n"
                    "запиши одну победу за день через /win"
                )
            else:
                txt = (
                    "🧠 День вышел сложным? Сделаем разбор без самокритики:\n"
                    "/slip"
                )
            await bot.send_message(user["user_id"], txt)
        except Exception as e:
            log.debug("reflection prompt skip %s: %s", user["user_id"], e)


def setup_scheduler(bot: Bot):
    scheduler.add_job(_morning, CronTrigger(hour=9, minute=0), args=[bot], id="morning")
    scheduler.add_job(_evening, CronTrigger(hour=21, minute=0), args=[bot], id="evening")
    scheduler.add_job(_kick, CronTrigger(hour="12,18", minute=0), args=[bot], id="kick")
    scheduler.add_job(
        _sweet_motivation,
        CronTrigger(hour="10,13,16,19,22", minute=0),
        args=[bot],
        id="sweet_motivation",
    )
    scheduler.add_job(
        _reflection_prompt,
        CronTrigger(hour=22, minute=30),
        args=[bot],
        id="reflection_prompt",
    )

    scheduler.start()
    log.info(
        "Scheduler started: morning=09:00 evening=21:00 kick=12:00/18:00 "
        "sweet=10/13/16/19/22 reflection=22:30"
    )
