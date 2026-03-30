import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router()


def _parse_minutes(text: str | None) -> int:
    if not text:
        return 25
    parts = text.split()
    if len(parts) == 2 and parts[1].isdigit():
        minutes = int(parts[1])
        return max(1, min(180, minutes))
    return 25


async def _finish_timer(message: Message, minutes: int):
    await asyncio.sleep(minutes * 60)
    await message.answer(f"🍅 Таймер {minutes} мин завершен. Сделай короткий перерыв 5 минут.")


@router.message(Command("pomodoro"))
@router.message(F.text == "🍅 Помодоро")
async def cmd_pomodoro(message: Message, state: FSMContext):
    await state.clear()
    minutes = _parse_minutes(message.text)

    asyncio.create_task(_finish_timer(message, minutes))
    await message.answer(
        f"🍅 Фокус-сессия на <b>{minutes} мин</b> запущена.\n"
        "Я напомню, когда время закончится.\n\n"
        "Подсказка: <code>/pomodoro 50</code> для глубокой сессии.",
        parse_mode="HTML",
    )
