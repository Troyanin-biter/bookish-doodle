from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from db.database import db

router = Router()


class WinState(StatesGroup):
    waiting_text = State()


class SlipState(StatesGroup):
    waiting_reason = State()
    waiting_action = State()


@router.message(Command("win"))
async def cmd_win(message: Message, state: FSMContext):
    await state.clear()
    raw = message.text or ""
    if raw.startswith("/win ") and len(raw) > 5:
        text = raw[5:].strip()
        if text:
            await db.add_win_entry(message.from_user.id, text)
            await message.answer("🌟 Записала в дневник побед. Ты молодец.")
            return

    await state.set_state(WinState.waiting_text)
    await message.answer("🌟 Напиши, чем ты сегодня гордишься:")


@router.message(WinState.waiting_text)
async def on_win_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши коротко одну победу за день.")
        return

    await db.add_win_entry(message.from_user.id, text)
    await state.clear()
    await message.answer("✅ Сохранила. Это важный шаг твоего роста.")


@router.message(Command("wins"))
async def cmd_wins(message: Message, state: FSMContext):
    await state.clear()
    items = await db.get_recent_wins(message.from_user.id, limit=10)
    if not items:
        await message.answer("Пока записей нет. Добавь первую через /win")
        return

    text = "📖 <b>Дневник побед (последние записи)</b>\n\n"
    for i, item in enumerate(items, start=1):
        text += f"{i}. {item['text']} <i>({item['created_at'][:16]})</i>\n"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("slip"))
async def cmd_slip(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SlipState.waiting_reason)
    await message.answer(
        "🧠 <b>Разбор срыва</b>\n\n"
        "Что помешало сегодня? Напиши честно и коротко.",
        parse_mode="HTML",
    )


@router.message(SlipState.waiting_reason)
async def on_slip_reason(message: Message, state: FSMContext):
    reason = (message.text or "").strip()
    if not reason:
        await message.answer("Опиши причину в 1-2 предложениях.")
        return

    await state.update_data(slip_reason=reason)
    await state.set_state(SlipState.waiting_action)
    await message.answer("Какой один шаг поможет завтра не повторить это?")


@router.message(SlipState.waiting_action)
async def on_slip_action(message: Message, state: FSMContext):
    action = (message.text or "").strip()
    if not action:
        await message.answer("Напиши один конкретный шаг на завтра.")
        return

    data = await state.get_data()
    reason = data.get("slip_reason", "Не указано")
    await db.add_slip_entry(message.from_user.id, reason, action)
    await state.clear()

    await message.answer(
        "✅ Разбор сохранен.\n\n"
        "Ты не провалился, ты учишься. Завтра начнем с этого шага:\n"
        f"👉 <b>{action}</b>",
        parse_mode="HTML",
    )


@router.message(Command("slips"))
async def cmd_slips(message: Message, state: FSMContext):
    await state.clear()
    items = await db.get_recent_slips(message.from_user.id, limit=5)
    if not items:
        await message.answer("Пока нет разборов. Если день сорвался, запусти /slip")
        return

    text = "🧠 <b>Твои последние разборы</b>\n\n"
    for i, item in enumerate(items, start=1):
        text += (
            f"{i}. Причина: {item['reason']}\n"
            f"   Шаг: <b>{item['action']}</b>\n"
            f"   <i>{item['created_at'][:16]}</i>\n\n"
        )
    await message.answer(text, parse_mode="HTML")

