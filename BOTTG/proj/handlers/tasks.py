from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db.database import db
from keyboards.keyboards import (
    PRIORITY_LABELS,
    confirm_delete,
    edit_priority_keyboard,
    task_actions,
    task_list,
)
from services.analytics import calculate_streak
from services.motivation import Motivation

router = Router()


class AddTask(StatesGroup):
    waiting_title = State()


class EditTask(StatesGroup):
    waiting_new_title = State()


def _safe_date(value: str) -> str | None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def _parse_task_payload(raw: str) -> tuple[str, int, str, str | None]:
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    title = parts[0] if parts else raw.strip()

    priority = 2
    category = "Общее"
    due_date = None

    for chunk in parts[1:]:
        low = chunk.lower()
        if low in {"p1", "p2", "p3"}:
            priority = int(low[-1])
            continue

        if low.startswith("cat:") or low.startswith("кат:"):
            _, value = chunk.split(":", 1)
            category = value.strip() or "Общее"
            continue

        if low.startswith("due:"):
            _, value = chunk.split(":", 1)
            due_date = _safe_date(value.strip())

    return title, priority, category, due_date


def _task_card(task: dict) -> str:
    status = "✅ Выполнена" if task["is_completed"] else "⬜ В работе"
    priority = PRIORITY_LABELS.get(task.get("priority", 2), "🟡 Средний")
    category = task.get("category") or "Общее"
    due = task.get("due_date") or "—"
    created = (task.get("created_at") or "")[:16]

    text = (
        f"📌 <b>Задача #{task['id']}</b>\n\n"
        f"📝 <b>{task['title']}</b>\n"
        f"📊 Статус: {status}\n"
        f"⚡ Приоритет: {priority}\n"
        f"🏷 Категория: <b>{category}</b>\n"
        f"⏰ Дедлайн: <b>{due}</b>\n"
        f"📅 Создана: {created}"
    )
    if task.get("completed_at"):
        text += f"\n✅ Завершена: {task['completed_at'][:16]}"
    return text


async def _save_task(message: Message, title: str, priority: int, category: str, due_date: str | None):
    if not title:
        await message.answer("❌ Пустое название. Попробуй ещё раз.")
        return

    task_id = await db.add_task(
        user_id=message.from_user.id,
        title=title,
        priority=priority,
        category=category,
        due_date=due_date,
    )
    await db.update_activity(message.from_user.id)

    due_text = f"\n⏰ Дедлайн: <b>{due_date}</b>" if due_date else ""
    text = (
        f"{Motivation.task_added()}\n\n"
        f"📌 <b>#{task_id}</b> {title}\n"
        f"⚡ {PRIORITY_LABELS.get(priority)}\n"
        f"🏷 {category}{due_text}"
    )
    await message.answer(text, parse_mode="HTML")


async def _show_tasks(target: Message | CallbackQuery, status: str = "all"):
    uid = target.from_user.id
    tasks = await db.get_tasks_filtered(uid, status=status)

    if not tasks:
        text = Motivation.no_tasks()
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text)
        else:
            await target.answer(text)
        return

    active = [t for t in tasks if not t["is_completed"]]
    done = [t for t in tasks if t["is_completed"]]
    text = (
        "🎨 <b>Твоя доска задач</b>\n\n"
        f"🟦 В работе: <b>{len(active)}</b>\n"
        f"🟩 Выполнено: <b>{len(done)}</b>\n"
        f"📚 Всего в этом фильтре: <b>{len(tasks)}</b>"
    )

    kb = task_list(tasks, current_filter=status)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.message(Command("add"))
@router.message(F.text.in_({"➕ Добавить", "➕ Добавить задачу"}))
async def cmd_add(message: Message, state: FSMContext):
    await state.clear()

    if message.text and message.text.startswith("/add ") and len(message.text) > 5:
        payload = message.text[5:].strip()
        title, priority, category, due_date = _parse_task_payload(payload)
        await _save_task(message, title, priority, category, due_date)
        return

    await state.set_state(AddTask.waiting_title)
    await message.answer(
        "📝 Напиши задачу в формате:\n"
        "<code>Текст | p1/p2/p3 | cat:Категория | due:YYYY-MM-DD</code>\n\n"
        "Пример:\n"
        "<code>Подготовить отчет | p1 | cat:Работа | due:2026-04-01</code>",
        parse_mode="HTML",
    )


@router.message(AddTask.waiting_title)
async def on_title(message: Message, state: FSMContext):
    if message.voice:
        await state.clear()
        await on_voice_task(message, state)
        return

    payload = (message.text or "").strip()
    title, priority, category, due_date = _parse_task_payload(payload)

    if not title:
        await message.answer("❌ Пустое название. Попробуй ещё раз:")
        return

    await state.clear()
    await _save_task(message, title, priority, category, due_date)


@router.message(Command("tasks"))
@router.message(F.text.in_({"📋 Задачи", "📋 Мои задачи"}))
async def cmd_tasks(message: Message, state: FSMContext):
    await state.clear()
    await db.update_activity(message.from_user.id)
    await _show_tasks(message, status="all")


@router.message(Command("today"))
@router.message(F.text == "📅 Сегодня")
async def cmd_today(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    tasks = await db.get_tasks_filtered(uid, status="active")
    today = datetime.now().strftime("%Y-%m-%d")
    due_today = [t for t in tasks if t.get("due_date") == today]

    text = (
        "📅 <b>Фокус на сегодня</b>\n\n"
        f"⏰ С дедлайном на сегодня: <b>{len(due_today)}</b>\n"
        f"📋 Активных всего: <b>{len(tasks)}</b>"
    )

    if due_today:
        text += "\n\n<b>Горящие:</b>\n"
        for task in due_today[:7]:
            text += f"• #{task['id']} {task['title']}\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("focus"))
@router.message(F.text == "🎯 Фокус дня")
async def cmd_focus(message: Message, state: FSMContext):
    await state.clear()
    tasks = await db.get_tasks_filtered(message.from_user.id, status="active", limit=3)

    if not tasks:
        await message.answer("🎯 Пока нет активных задач. Добавь первую через /add")
        return

    text = "🎯 <b>3 задачи фокуса</b>\n\n"
    for i, task in enumerate(tasks, start=1):
        due = f" · дедлайн {task['due_date']}" if task.get("due_date") else ""
        text += (
            f"{i}. <b>#{task['id']} {task['title']}</b>\n"
            f"   {PRIORITY_LABELS.get(task.get('priority', 2))} · {task.get('category', 'Общее')}{due}\n"
        )

    text += "\nСовет: закрой первую задачу в ближайшие 30 минут."
    await message.answer(text, parse_mode="HTML")


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await state.clear()
    query = ""
    if message.text and message.text.startswith("/search "):
        query = message.text[8:].strip()

    if not query:
        await message.answer("🔎 Использование: <code>/search текст</code>", parse_mode="HTML")
        return

    tasks = await db.get_tasks_filtered(message.from_user.id, status="all", search=query, limit=15)
    if not tasks:
        await message.answer("🔎 Ничего не найдено.")
        return

    text = f"🔎 <b>Найдено: {len(tasks)}</b>\n\n"
    for task in tasks:
        status = "✅" if task["is_completed"] else "⬜"
        text += f"{status} #{task['id']} {task['title']}\n"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext):
    await state.clear()
    if not message.text or len(message.text.split()) != 2 or not message.text.split()[1].isdigit():
        await message.answer("Использование: <code>/done ID</code>", parse_mode="HTML")
        return

    task_id = int(message.text.split()[1])
    await db.complete_task(task_id, message.from_user.id)
    await message.answer(f"✅ Задача #{task_id} отмечена выполненной.")


@router.message(Command("undo"))
async def cmd_undo(message: Message, state: FSMContext):
    await state.clear()
    if not message.text or len(message.text.split()) != 2 or not message.text.split()[1].isdigit():
        await message.answer("Использование: <code>/undo ID</code>", parse_mode="HTML")
        return

    task_id = int(message.text.split()[1])
    await db.reopen_task(task_id, message.from_user.id)
    await message.answer(f"↩️ Задача #{task_id} снова активна.")


@router.message(F.voice)
async def on_voice_task(message: Message, state: FSMContext):
    await state.clear()
    caption = (message.caption or "").strip()
    duration = message.voice.duration if message.voice else 0

    if caption:
        title = f"🎙 {caption}"
    else:
        title = f"🎙 Голосовая заметка ({duration} сек) — уточни текстом при необходимости"

    task_id = await db.add_task(
        user_id=message.from_user.id,
        title=title,
        priority=2,
        category="Голосовые",
        due_date=None,
    )
    await db.update_activity(message.from_user.id)
    await message.answer(
        "🎙 Голосовую задачу сохранила.\n"
        f"📌 <b>#{task_id}</b> {title}\n\n"
        "Совет: отправь голосовое с подписью, и я сохраню её как текст задачи.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("filter:"))
async def cb_filter(cb: CallbackQuery):
    status = cb.data.split(":")[1]
    await _show_tasks(cb, status=status)
    await cb.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


@router.callback_query(F.data.startswith("info:"))
async def cb_info(cb: CallbackQuery):
    task = await db.get_task(int(cb.data.split(":")[1]))
    if not task or task.get("user_id") != cb.from_user.id:
        await cb.answer("Задача не найдена", show_alert=True)
        return

    await cb.message.edit_text(
        _task_card(task),
        reply_markup=task_actions(task["id"], bool(task["is_completed"])).as_markup(),
        parse_mode="HTML",
    )
    await cb.answer()


@router.callback_query(F.data.startswith("done:"))
async def cb_done(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[1])
    uid = cb.from_user.id

    await db.complete_task(task_id, uid)
    await db.update_activity(uid)

    today = await db.get_completed_today(uid)
    active = await db.get_active_tasks(uid)
    streak = await calculate_streak(uid)

    text = Motivation.task_completed(today, len(active))
    smsg = Motivation.streak(streak)
    if smsg:
        text += f"\n\n{smsg}"

    await cb.message.edit_text(text)
    await cb.answer("✅ Выполнено")


@router.callback_query(F.data.startswith("undo:"))
async def cb_undo(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[1])
    await db.reopen_task(task_id, cb.from_user.id)
    task = await db.get_task(task_id)
    if not task or task.get("user_id") != cb.from_user.id:
        await cb.answer("Задача не найдена", show_alert=True)
        return
    await cb.message.edit_text(_task_card(task), parse_mode="HTML")
    await cb.answer("↩️ Вернул в работу")


@router.callback_query(F.data.startswith("del:"))
async def cb_del(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[1])
    task = await db.get_task(task_id)
    if not task or task.get("user_id") != cb.from_user.id:
        await cb.answer("Задача не найдена", show_alert=True)
        return
    title = task["title"] if task else "эту задачу"
    await cb.message.edit_text(
        f"🗑 Удалить «{title}»?",
        reply_markup=confirm_delete(task_id).as_markup(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("confirm_del:"))
async def cb_confirm_del(cb: CallbackQuery):
    task_id = int(cb.data.split(":")[1])
    await db.delete_task(task_id, cb.from_user.id)
    await cb.message.edit_text("🗑 Задача удалена.")
    await cb.answer()


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit(cb: CallbackQuery, state: FSMContext):
    task_id = int(cb.data.split(":")[1])
    task = await db.get_task(task_id)
    if not task or task.get("user_id") != cb.from_user.id:
        await cb.answer("Задача не найдена", show_alert=True)
        return

    await state.set_state(EditTask.waiting_new_title)
    await state.update_data(edit_task_id=task_id)

    await cb.message.answer(
        "✏️ Отправь новый текст задачи.\n"
        "Или поменяй приоритет кнопками ниже:",
        reply_markup=edit_priority_keyboard(task_id).as_markup(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("set_priority:"))
async def cb_set_priority(cb: CallbackQuery):
    _, task_id_raw, priority_raw = cb.data.split(":")
    task_id = int(task_id_raw)
    priority = int(priority_raw)

    task = await db.get_task(task_id)
    if not task or task.get("user_id") != cb.from_user.id:
        await cb.answer("Задача не найдена", show_alert=True)
        return

    await db.update_task(task_id, cb.from_user.id, priority=priority)
    task = await db.get_task(task_id)
    await cb.message.edit_text(
        _task_card(task),
        reply_markup=task_actions(task_id, bool(task["is_completed"])).as_markup(),
        parse_mode="HTML",
    )
    await cb.answer("⚡ Приоритет обновлен")


@router.message(EditTask.waiting_new_title)
async def on_new_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("❌ Пустой текст. Попробуй снова.")
        return

    data = await state.get_data()
    task_id = data.get("edit_task_id")
    if not task_id:
        await state.clear()
        await message.answer("Не удалось определить задачу. Открой её заново в списке.")
        return

    await db.update_task(task_id, message.from_user.id, title=title)
    await state.clear()

    task = await db.get_task(task_id)
    await message.answer("✅ Название обновлено.")
    await message.answer(
        _task_card(task),
        reply_markup=task_actions(task_id, bool(task["is_completed"])).as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "back")
async def cb_back(cb: CallbackQuery):
    await _show_tasks(cb, status="all")
    await cb.answer()


@router.callback_query(F.data == "add_task")
async def cb_add_inline(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddTask.waiting_title)
    await cb.message.answer("📝 Напиши задачу в формате: Текст | p1 | cat:Категория | due:YYYY-MM-DD")
    await cb.answer()




