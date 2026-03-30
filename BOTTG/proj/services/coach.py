from datetime import date, timedelta


def split_complex_task(task_text: str) -> list[str]:
    base = task_text.strip()
    if not base:
        return [
            "Определи конкретный результат в одном предложении.",
            "Подготовь все материалы и открой нужные вкладки.",
            "Сделай первую маленькую часть за 15 минут.",
            "Проверь, что получилось, и поправь главное.",
            "Зафиксируй прогресс и назначь следующий шаг.",
        ]

    return [
        f"Уточни результат задачи: «{base}». Что значит «готово»?",
        "Собери входные данные/материалы (до 10 минут).",
        "Сделай черновой вариант без перфекционизма (20-30 минут).",
        "Улучши самое важное: 1-2 правки с максимальным эффектом.",
        "Заверши и отметь выполнение или запланируй следующий слот.",
    ]


def quick_reset_steps(mood: str) -> str:
    if mood == "low":
        return (
            "⚡ <b>Быстрый перезапуск (мягкий режим)</b>\n\n"
            "1. 4 медленных вдоха и выдоха.\n"
            "2. Вода + умыться.\n"
            "3. 1 микро-задача на 5 минут.\n"
            "4. Небольшая пауза 2 минуты.\n"
            "5. Еще один короткий шаг.\n\n"
            "Тебе не нужно идеально. Нужно просто вернуться в движение."
        )
    if mood == "high":
        return (
            "⚡ <b>Быстрый перезапуск (боевой режим)</b>\n\n"
            "1. Таймер 25 минут.\n"
            "2. Самая важная задача - сразу в работу.\n"
            "3. Ноль переключений до сигнала таймера.\n"
            "4. Короткий чек: что закрыто?\n"
            "5. Второй спринт.\n\n"
            "Ты в хорошем темпе. Держи фокус."
        )
    return (
        "⚡ <b>Быстрый перезапуск</b>\n\n"
        "1. Убери лишние вкладки/уведомления.\n"
        "2. Поставь таймер на 15 минут.\n"
        "3. Сделай первый понятный шаг по задаче.\n"
        "4. Отметь прогресс и выбери следующий шаг.\n\n"
        "Главное правило: маленький шаг > откладывание."
    )


def rewards_snapshot(total_done: int, streak: int, weekly_done: int) -> str:
    coins = total_done * 5 + streak * 3 + weekly_done * 2
    rewards = [
        (80, "🎬 1 серия/фильм без чувства вины"),
        (140, "🍔 Любимая вкусняшка"),
        (220, "🎮 Игровой вечер"),
        (320, "🛍 Небольшая покупка себе"),
        (500, "🎁 Большая награда недели"),
    ]

    available = [label for threshold, label in rewards if coins >= threshold]
    next_target = next((r for r in rewards if coins < r[0]), None)

    text = (
        "🎁 <b>Награды за прогресс</b>\n\n"
        f"🪙 Твои поинты: <b>{coins}</b>\n"
        f"✅ Выполнено всего: {total_done}\n"
        f"🔥 Серия: {streak} дн.\n"
        f"📈 За 7 дней: {weekly_done}\n\n"
    )

    if available:
        text += "<b>Уже можешь забрать:</b>\n"
        for item in available[-2:]:
            text += f"• {item}\n"
    else:
        text += "Пока копим поинты. Первый приз уже близко.\n"

    if next_target:
        need = next_target[0] - coins
        text += f"\nДо следующей награды: <b>{need}</b> поинтов\n🎯 {next_target[1]}"

    return text


def build_week_plan(tasks: list[dict], mood: str) -> str:
    if not tasks:
        return (
            "🗓 <b>Умный планер недели</b>\n\n"
            "Пока нет активных задач. Добавь задачи через /add, и я разложу их по дням."
        )

    pace_hint = {
        "low": "мягкий темп: 1-2 задачи в день",
        "normal": "стабильный темп: 2 задачи в день",
        "high": "интенсивный темп: 2-3 задачи в день",
    }.get(mood, "стабильный темп: 2 задачи в день")

    week_days = []
    start = date.today()
    for i in range(7):
        d = start + timedelta(days=i)
        week_days.append((d.strftime("%a"), d.strftime("%Y-%m-%d")))

    # Expected input order is already prioritized from DB.
    top = tasks[:14]
    buckets = {i: [] for i in range(7)}
    for i, task in enumerate(top):
        buckets[i % 7].append(task)

    text = "🗓 <b>Умный планер недели</b>\n\n"
    text += f"Твой режим сейчас: <b>{pace_hint}</b>\n\n"

    for idx, (short_day, day_full) in enumerate(week_days):
        text += f"<b>{short_day} ({day_full})</b>\n"
        if not buckets[idx]:
            text += "• Лёгкий день / отдых\n"
            continue
        for task in buckets[idx][:3]:
            due = f" · дедлайн {task['due_date']}" if task.get("due_date") else ""
            text += f"• #{task['id']} {task['title']}{due}\n"
        text += "\n"

    text += "Совет: каждый день закрывай минимум 1 задачу, чтобы не терять серию."
    return text

