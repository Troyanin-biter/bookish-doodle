import random

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db.database import db
from keyboards.keyboards import mood_menu, motivation_menu
from services.analytics import calculate_streak
from services.coach import build_week_plan, quick_reset_steps, rewards_snapshot, split_complex_task
from services.comfort import (
    anti_procrastination_base,
    needed_quote,
    power_quote,
    quote_of_day,
    soft_support,
    sos_message,
)

router = Router()


class SplitTaskState(StatesGroup):
    waiting_text = State()


def _mood_human(mood: str) -> str:
    return {
        "low": "🌧 Низкий заряд",
        "normal": "🌤 Нормальный",
        "high": "☀️ Полон сил",
    }.get(mood, "🌤 Нормальный")


def _build_achievements(total_done: int, streak: int, completed_today: int, pending: int, total: int) -> str:
    checks = [
        (total_done >= 1, "Первый шаг", "Закрыть 1 задачу"),
        (total_done >= 10, "Разгон", "Закрыть 10 задач"),
        (total_done >= 50, "Стабильность", "Закрыть 50 задач"),
        (streak >= 3, "Серия 3", "3 дня подряд"),
        (streak >= 7, "Серия 7", "7 дней подряд"),
        (streak >= 30, "Серия 30", "30 дней подряд"),
        (completed_today >= 3, "Мощный день", "3 задачи за сегодня"),
        (pending == 0 and total > 0, "Чистый лист", "Не оставить активных задач"),
    ]

    text = "🏅 <b>Твои достижения</b>\n\n"
    for unlocked, title, goal in checks:
        icon = "✅" if unlocked else "🔒"
        text += f"{icon} <b>{title}</b> - {goal}\n"

    unlocked_count = len([1 for item in checks if item[0]])
    text += f"\nПрогресс: <b>{unlocked_count}/{len(checks)}</b> достижений"
    return text


async def _motivation_text(mode: str, user_id: int) -> str:
    mood = await db.get_user_mood(user_id)

    if mode == "day":
        return f"🌸 <b>Цитата дня</b>\n\n<i>{quote_of_day()}</i>"

    if mode == "support":
        return f"🫶 <b>Мягкая поддержка</b>\n\n<i>{soft_support()}</i>"

    if mode == "power":
        return f"🔥 <b>Боевой заряд</b>\n\n<i>{power_quote()}</i>"

    if mode == "sos":
        return sos_message()

    if mode == "anti":
        tasks = await db.get_tasks_filtered(user_id, status="active", limit=1)
        text = anti_procrastination_base()
        if tasks:
            text += f"\n\n🎯 Попробуй начать с этого:\n<b>#{tasks[0]['id']} {tasks[0]['title']}</b>"
        return text

    if mode == "achievements":
        total = await db.get_total_stats(user_id)
        streak = await calculate_streak(user_id)
        completed_today = await db.get_completed_today(user_id)
        return _build_achievements(
            total_done=total["completed"],
            streak=streak,
            completed_today=completed_today,
            pending=total["pending"],
            total=total["total"],
        )

    if mode == "rewards":
        total = await db.get_total_stats(user_id)
        streak = await calculate_streak(user_id)
        weekly = await db.get_stats_period(user_id, days=7)
        return rewards_snapshot(total_done=total["completed"], streak=streak, weekly_done=weekly["total_completed"])

    if mode == "reset":
        return quick_reset_steps(mood)

    if mode == "weekplan":
        tasks = await db.get_tasks_filtered(user_id, status="active", limit=30)
        return build_week_plan(tasks, mood)

    if mode == "plan":
        tasks = await db.get_tasks_filtered(user_id, status="active", limit=3)
        if not tasks:
            return (
                "🎯 <b>Мини-план на сейчас</b>\n\n"
                "1. Выпей воды\n"
                "2. Выбери одну простую задачу\n"
                "3. Сделай её за 15 минут\n\n"
                "Ты справишься. Начни с малого, и дальше станет легче."
            )

        text = "🎯 <b>Мини-план на сейчас</b>\n\n"
        for i, task in enumerate(tasks, start=1):
            text += f"{i}. {task['title']}\n"
        text += "\nНачни с пункта 1. Я верю в тебя."
        return text

    return f"💌 <b>Цитата, которая тебе нужна</b>\n\n<i>{needed_quote()}</i>"


def _split_result(task_text: str) -> str:
    steps = split_complex_task(task_text)
    text = "🧩 <b>Разбивка сложной задачи</b>\n\n"
    if task_text.strip():
        text += f"Задача: <b>{task_text.strip()}</b>\n\n"
    for i, step in enumerate(steps, start=1):
        text += f"{i}. {step}\n"
    text += "\nНачни с первого шага на 10-15 минут."
    return text


@router.message(Command("motivation"))
@router.message(F.text == "💖 Мотивация")
async def cmd_motivation(message: Message, state: FSMContext):
    await state.clear()
    await db.update_activity(message.from_user.id)
    mood = await db.get_user_mood(message.from_user.id)
    await message.answer(
        "💖 <b>Твоя вкладка мотивации</b>\n\n"
        f"Текущий режим настроения: <b>{_mood_human(mood)}</b>\n"
        "Выбирай, что тебе нужно прямо сейчас:",
        reply_markup=motivation_menu().as_markup(),
        parse_mode="HTML",
    )


@router.message(Command("anti"))
async def cmd_anti(message: Message, state: FSMContext):
    await state.clear()
    text = await _motivation_text("anti", message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("sos"))
async def cmd_sos(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _motivation_text("sos", message.from_user.id), parse_mode="HTML")


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _motivation_text("achievements", message.from_user.id), parse_mode="HTML")


@router.message(Command("rewards"))
async def cmd_rewards(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _motivation_text("rewards", message.from_user.id), parse_mode="HTML")


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _motivation_text("reset", message.from_user.id), parse_mode="HTML")


@router.message(Command("weekplan"))
@router.message(F.text == "🗓 Планер недели")
async def cmd_weekplan(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _motivation_text("weekplan", message.from_user.id), parse_mode="HTML")


@router.message(Command("mood"))
async def cmd_mood(message: Message, state: FSMContext):
    await state.clear()
    mood = await db.get_user_mood(message.from_user.id)
    await message.answer(
        f"🎭 <b>Режим настроения</b>\n\nСейчас: <b>{_mood_human(mood)}</b>\nВыбери, как ты себя чувствуешь:",
        reply_markup=mood_menu().as_markup(),
        parse_mode="HTML",
    )


@router.message(Command("split"))
async def cmd_split(message: Message, state: FSMContext):
    await state.clear()
    raw = message.text or ""
    if raw.startswith("/split ") and len(raw) > 7:
        task_text = raw[7:].strip()
        await message.answer(_split_result(task_text), parse_mode="HTML")
        return

    await state.set_state(SplitTaskState.waiting_text)
    await message.answer("🧩 Напиши сложную задачу, и я разложу её на шаги.")


@router.message(SplitTaskState.waiting_text)
async def on_split_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    await state.clear()
    await message.answer(_split_result(text), parse_mode="HTML")


@router.callback_query(F.data.startswith("mood:"))
async def cb_set_mood(cb: CallbackQuery):
    mood = cb.data.split(":")[1]
    if mood not in {"low", "normal", "high"}:
        await cb.answer("Неизвестный режим", show_alert=True)
        return

    await db.set_user_mood(cb.from_user.id, mood)
    await cb.message.edit_text(
        f"🎭 <b>Режим обновлен:</b> {_mood_human(mood)}\n\n"
        "Теперь советы и перезапуск будут подстраиваться под твое состояние.",
        reply_markup=motivation_menu().as_markup(),
        parse_mode="HTML",
    )
    await cb.answer("Сохранила режим")


@router.callback_query(F.data.startswith("mot:"))
async def cb_motivation(cb: CallbackQuery, state: FSMContext):
    mode = cb.data.split(":")[1]
    await db.update_activity(cb.from_user.id)

    if mode == "more":
        mode = random.choice(["needed", "support", "power", "anti", "reset"])

    if mode == "mood":
        mood = await db.get_user_mood(cb.from_user.id)
        await cb.message.edit_text(
            f"🎭 <b>Режим настроения</b>\n\nСейчас: <b>{_mood_human(mood)}</b>\nВыбери новый режим:",
            reply_markup=mood_menu().as_markup(),
            parse_mode="HTML",
        )
        await cb.answer()
        return

    if mode == "split":
        await state.set_state(SplitTaskState.waiting_text)
        await cb.message.answer("🧩 Напиши задачу, и я разобью её на маленькие шаги.")
        await cb.answer()
        return

    text = await _motivation_text(mode, cb.from_user.id)
    await cb.message.edit_text(text, reply_markup=motivation_menu().as_markup(), parse_mode="HTML")
    await cb.answer()
