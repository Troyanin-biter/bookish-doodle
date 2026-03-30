from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "ℹ️ <b>Гид по боту</b>\n\n"
        "<b>Задачи</b>\n"
        "• /add - добавить задачу\n"
        "• /add Текст | p1 | cat:Работа | due:2026-04-01\n"
        "• /tasks - список задач\n"
        "• /done ID - закрыть\n"
        "• /undo ID - вернуть в работу\n"
        "• /search текст - поиск\n\n"
        "<b>Фокус</b>\n"
        "• /today - что важно сегодня\n"
        "• /focus - топ-3 приоритета\n"
        "• /pomodoro 25 - таймер фокуса\n\n"
        "<b>Мотивация</b>\n"
        "• /motivation - вкладка поддержки\n"
        "• Цитата, которая тебе нужна\n"
        "• Цитата дня и антистресс-поддержка\n\n"
        "• /anti - старт против прокрастинации\n"
        "• /sos - быстрая поддержка в тяжёлый момент\n"
        "• /achievements - твои достижения\n\n"
        "• /rewards - награды за прогресс\n"
        "• /mood - режим настроения\n"
        "• /split задача - разбивка сложной задачи\n"
        "• /reset - быстрый перезапуск\n"
        "• /weekplan - умный планер недели\n\n"
        "<b>Рефлексия</b>\n"
        "• /win - добавить запись в дневник побед\n"
        "• /wins - посмотреть дневник побед\n"
        "• /slip - разбор срыва\n"
        "• /slips - история разборов\n\n"
        "<b>Голосовые задачи</b>\n"
        "• Отправь голосовое, и я сохраню его как задачу\n"
        "• Добавь подпись к голосовому для точного текста\n\n"
        "<b>Аналитика</b>\n"
        "• /stats - полная статистика\n"
        "• /report - недельный срез\n"
        "• /profile - уровень и очки\n\n"
        "<b>Совет</b>\n"
        "Ставь дедлайн и приоритет в момент добавления - так бот точнее подсказывает фокус.",
        parse_mode="HTML",
    )
