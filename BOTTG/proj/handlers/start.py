from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from db.database import db
from keyboards.keyboards import main_menu
from services.motivation import Motivation

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    user = await db.get_user(uid)

    if user:
        try:
            last = datetime.strptime(user["last_active_at"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            last = datetime.now()

        if datetime.now() - last > timedelta(days=3):
            text = (
                f"{Motivation.comeback()}\n\n"
                "Твой прогресс сохранен. Продолжаем прокачку продуктивности."
            )
        else:
            text = (
                f"С возвращением, <b>{message.from_user.first_name}</b>.\n"
                "Готов закрывать задачи и собирать серию дней?"
            )
    else:
        await db.add_user(uid, message.from_user.username, message.from_user.first_name)
        text = (
            f"Привет, <b>{message.from_user.first_name}</b>.\n\n"
            "Я твой бот-ассистент продуктивности.\n"
            "Помогаю вести задачи, держать фокус и видеть реальный прогресс.\n\n"
            "Что умею:\n"
            "• гибкие задачи с приоритетом, категорией и дедлайном\n"
            "• фокус дня и подбор 3 главных задач\n"
            "• статистика, серия дней и профиль\n"
            "• помодоро-таймер для спринтов\n\n"
            "Жми <b>➕ Добавить</b> и начнем."
        )

    await db.update_activity(uid)
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
