from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PRIORITY_LABELS = {
    1: "🔴 Важный",
    2: "🟡 Средний",
    3: "🟢 Низкий",
}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Задачи"), KeyboardButton(text="➕ Добавить")],
            [KeyboardButton(text="🎯 Фокус дня"), KeyboardButton(text="📅 Сегодня")],
            [KeyboardButton(text="🗓 Планер недели"), KeyboardButton(text="📈 Неделя")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💖 Мотивация")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🍅 Помодоро")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие или введи команду /help",
    )


def task_list(tasks: list[dict], current_filter: str = "all") -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()

    for task in tasks[:20]:
        status_icon = "✅" if task["is_completed"] else "⬜"
        priority_icon = {1: "🔴", 2: "🟡", 3: "🟢"}.get(task.get("priority", 2), "🟡")
        due = f" • ⏰ {task['due_date']}" if task.get("due_date") else ""
        label = f"{status_icon} {priority_icon} {task['title'][:25]}{due}"
        kb.row(InlineKeyboardButton(text=label, callback_data=f"info:{task['id']}"))

    kb.row(
        InlineKeyboardButton(text="🟦 Активные", callback_data="filter:active"),
        InlineKeyboardButton(text="🟩 Выполненные", callback_data="filter:done"),
    )
    kb.row(
        InlineKeyboardButton(text="📚 Все", callback_data="filter:all"),
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_task"),
    )
    kb.row(InlineKeyboardButton(text=f"Текущий фильтр: {current_filter}", callback_data="noop"))
    return kb


def task_actions(task_id: int, done: bool) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if not done:
        kb.row(InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done:{task_id}"))
    else:
        kb.row(InlineKeyboardButton(text="↩️ Вернуть в работу", callback_data=f"undo:{task_id}"))

    kb.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{task_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{task_id}"),
    )
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return kb


def confirm_delete(task_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del:{task_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="back"),
    )
    return kb


def edit_priority_keyboard(task_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🔴 1", callback_data=f"set_priority:{task_id}:1"),
        InlineKeyboardButton(text="🟡 2", callback_data=f"set_priority:{task_id}:2"),
        InlineKeyboardButton(text="🟢 3", callback_data=f"set_priority:{task_id}:3"),
    )
    kb.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"info:{task_id}"))
    return kb


def motivation_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎭 Режим настроения", callback_data="mot:mood"))
    kb.row(InlineKeyboardButton(text="💌 Цитата, которая тебе нужна", callback_data="mot:needed"))
    kb.row(InlineKeyboardButton(text="🌸 Цитата дня", callback_data="mot:day"))
    kb.row(InlineKeyboardButton(text="⏱ Антипрокрастинация", callback_data="mot:anti"))
    kb.row(InlineKeyboardButton(text="🫶 Мягкая поддержка", callback_data="mot:support"))
    kb.row(InlineKeyboardButton(text="🔥 Боевой заряд", callback_data="mot:power"))
    kb.row(InlineKeyboardButton(text="🆘 SOS-поддержка", callback_data="mot:sos"))
    kb.row(InlineKeyboardButton(text="⚡ Быстрый перезапуск", callback_data="mot:reset"))
    kb.row(InlineKeyboardButton(text="🧩 Разбить сложную задачу", callback_data="mot:split"))
    kb.row(InlineKeyboardButton(text="🎯 Мини-план на сейчас", callback_data="mot:plan"))
    kb.row(InlineKeyboardButton(text="🗓 Умный планер недели", callback_data="mot:weekplan"))
    kb.row(InlineKeyboardButton(text="🏅 Достижения", callback_data="mot:achievements"))
    kb.row(InlineKeyboardButton(text="🎁 Награды за прогресс", callback_data="mot:rewards"))
    kb.row(InlineKeyboardButton(text="🔄 Ещё мотивацию", callback_data="mot:more"))
    return kb


def mood_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🌧 Низкий заряд", callback_data="mood:low"),
        InlineKeyboardButton(text="🌤 Нормально", callback_data="mood:normal"),
        InlineKeyboardButton(text="☀️ Полон сил", callback_data="mood:high"),
    )
    kb.row(InlineKeyboardButton(text="◀️ Назад в мотивацию", callback_data="mot:needed"))
    return kb
