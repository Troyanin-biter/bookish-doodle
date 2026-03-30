from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.database import db
from services.analytics import calculate_streak

router = Router()


RANKS = [
    (1, "🌱 Новичок"),
    (3, "⚡ Включился"),
    (5, "🔥 В ритме"),
    (8, "🧠 Дисциплина"),
    (12, "🏆 Мастер фокуса"),
    (16, "👑 Легенда продуктивности"),
]


def _level_from_points(points: int) -> tuple[int, int, int]:
    level = max(1, points // 100 + 1)
    prev_border = (level - 1) * 100
    next_border = level * 100
    return level, prev_border, next_border


def _rank_for_level(level: int) -> str:
    current = RANKS[0][1]
    for border, title in RANKS:
        if level >= border:
            current = title
    return current


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id

    total = await db.get_total_stats(uid)
    completed_today = await db.get_completed_today(uid)
    streak = await calculate_streak(uid)
    due_today = await db.get_due_today_count(uid)

    points = total["completed"] * 10 + streak * 5
    level, prev_border, next_border = _level_from_points(points)
    rank = _rank_for_level(level)
    progress = points - prev_border
    needed = next_border - prev_border

    text = (
        "👤 <b>Профиль продуктивности</b>\n\n"
        f"🎮 Ранг: <b>{rank}</b>\n"
        f"🏆 Уровень: <b>{level}</b>\n"
        f"⭐ Очки: <b>{points}</b> ({progress}/{needed})\n"
        f"🔥 Серия: <b>{streak}</b> дн.\n\n"
        f"✅ Выполнено всего: <b>{total['completed']}</b>\n"
        f"⬜ В работе: <b>{total['pending']}</b>\n"
        f"📅 Закрыто сегодня: <b>{completed_today}</b>\n"
        f"⏰ Дедлайнов сегодня: <b>{due_today}</b>\n"
        f"📊 Процент выполнения: <b>{total['completion_rate']}%</b>"
    )

    await message.answer(text, parse_mode="HTML")
