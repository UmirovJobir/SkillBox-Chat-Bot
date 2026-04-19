from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню — кнопки снизу экрана.
    resize_keyboard=True — кнопки меньшего размера, не занимают пол-экрана.
    row_width=2 — 2 кнопки в строку.
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📋 Мои привычки"),
        KeyboardButton("➕ Добавить привычку"),
        KeyboardButton("⏰ Настроить уведомление"),
        KeyboardButton("ℹ️ Помощь"),
    )
    return keyboard


def build_auth_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопки выбора: войти или зарегистрироваться.
    Inline кнопки — под сообщением.
    callback_data — строка, которую бот получит при нажатии.
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 Регистрация", callback_data="auth_register"),
        InlineKeyboardButton("🔑 Войти", callback_data="auth_login"),
    )
    return keyboard


def build_habits_list_keyboard(habits: list) -> InlineKeyboardMarkup:
    """
    Список привычек в виде кнопок.
    Каждая кнопка: статус + название + прогресс (3/21)
    callback_data = "habit_view_5" → хендлер знает: показать привычку с id=5
    """
    keyboard = InlineKeyboardMarkup(row_width=1)
    for habit in habits:
        status_emoji = "✅" if habit.get("is_completed_today") else "⭕"
        progress = f"{habit['total_completions']}/{habit['target_completions']}"
        keyboard.add(
            InlineKeyboardButton(
                text=f"{status_emoji} {habit['title']} ({progress})",
                callback_data=f"habit_view_{habit['id']}",
            )
        )
    return keyboard


def build_habit_actions_keyboard(
    habit_id: int,
    is_completed_today: bool,
) -> InlineKeyboardMarkup:
    """
    Кнопки действий для конкретной привычки.
    "Выполнено" показываем только если привычка ещё не отмечена сегодня.
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    if not is_completed_today:
        keyboard.add(
            InlineKeyboardButton(
                "✅ Выполнено",
                callback_data=f"habit_done_{habit_id}",
            )
        )
    keyboard.add(
        InlineKeyboardButton("✏️ Изменить", callback_data=f"habit_edit_{habit_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"habit_delete_{habit_id}"),
    )
    keyboard.add(
        InlineKeyboardButton("◀️ Назад к списку", callback_data="habits_list")
    )
    return keyboard


def build_edit_habit_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    """Меню выбора: что именно редактировать в привычке."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(
            "📝 Изменить название", callback_data=f"edit_title_{habit_id}"
        ),
        InlineKeyboardButton(
            "📄 Изменить описание", callback_data=f"edit_desc_{habit_id}"
        ),
        InlineKeyboardButton(
            "🎯 Изменить цель (дни)", callback_data=f"edit_target_{habit_id}"
        ),
        InlineKeyboardButton("◀️ Назад", callback_data=f"habit_view_{habit_id}"),
    )
    return keyboard


def build_confirm_delete_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления — защита от случайного нажатия."""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            "✅ Да, удалить",
            callback_data=f"habit_confirm_delete_{habit_id}",
        ),
        InlineKeyboardButton(
            "❌ Отмена", callback_data=f"habit_view_{habit_id}"
        ),
    )
    return keyboard