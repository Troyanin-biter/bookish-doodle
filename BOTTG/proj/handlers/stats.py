from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.database import db
from services.analytics import full_stats, weekly_report

router = Router()


def _bar(pct: float) -> str:
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled)


def _verdict(rate: float) -> str:
    if rate >= 80:
        return "Отличный темп. Ты в сильной форме."
    if rate >= 50:
        return "Хороший прогресс. Поднажмем до 80%."
    if rate >= 20:
        return "Есть движение, но нужен стабильный ритм."
    return "Пора включаться. Начни с 1-2 простых задач сегодня."


@router.message(Command("stats"))
@router.message(F.text.in_({"📊 Статистика", "📉 Статистика", "📊 Статистика"}))
async def cmd_stats(message: Message, state: FSMContext):
    await state.clear()
    await db.update_activity(message.from_user.id)
    st = await full_stats(message.from_user.id)
    t = st["total"]

    if t["total"] == 0:
        await message.answer("📊 Пока нет статистики. Добавь задачи через /add и начни движение.")
        return

    text = (
        "📊 <b>Твоя статистика</b>\n\n"
        "<b>Общие</b>\n"
        f"• Всего задач: {t['total']}\n"
        f"• Выполнено: {t['completed']}\n"
        f"• В работе: {t['pending']}\n"
        f"• Процент: {t['completion_rate']}%\n\n"
        f"🔥 Серия: <b>{st['streak']}</b> дн.\n\n"
        "<b>За 7 дней</b>\n"
        f"• Создано: {st['weekly']['total_created']}\n"
        f"• Выполнено: {st['weekly']['total_completed']}\n"
        f"• Процент: {st['weekly']['completion_rate']}%\n\n"
        "<b>За 30 дней</b>\n"
        f"• Создано: {st['monthly']['total_created']}\n"
        f"• Выполнено: {st['monthly']['total_completed']}\n"
        f"• Процент: {st['monthly']['completion_rate']}%\n"
    )

    if st["best_day"]:
        text += f"\n🏅 Лучший день: {st['best_day']}\n"

    text += f"\n<code>[{_bar(t['completion_rate'])}] {t['completion_rate']}%</code>"
    text += f"\n\n{_verdict(t['completion_rate'])}"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("report"))
@router.message(F.text.in_({"📈 Неделя", "📈 Нед. отчет", "📈 Нед. отчёт"}))
async def cmd_report(message: Message, state: FSMContext):
    await state.clear()
    await db.update_activity(message.from_user.id)
    rpt = await weekly_report(message.from_user.id)

    if rpt["total_created"] == 0:
        await message.answer("📈 За неделю пока нет данных. Добавь несколько задач для анализа.")
        return

    text = (
        "📈 <b>Недельный отчет</b>\n\n"
        f"📋 Создано: {rpt['total_created']}\n"
        f"✅ Выполнено: {rpt['total_completed']}\n"
        f"📊 Процент: {rpt['completion_rate']}%\n"
        f"🔥 Серия: {rpt['streak']} дн.\n"
        f"<code>[{_bar(rpt['completion_rate'])}] {rpt['completion_rate']}%</code>\n"
    )

    if rpt["best_day"]:
        text += f"\n🏅 Лучший день: {rpt['best_day']}"
    if rpt["worst_day"]:
        text += f"\n🧩 Слабее всего: {rpt['worst_day']}"

    if rpt["daily_completions"]:
        text += "\n\n<b>По дням:</b>\n"
        for day, cnt in rpt["daily_completions"]:
            text += f"• {day}: {'✅' * min(cnt, 10)} ({cnt})\n"

    await message.answer(text, parse_mode="HTML")
