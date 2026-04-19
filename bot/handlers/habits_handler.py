import telebot
from telebot.types import CallbackQuery, Message

from handlers.auth_handler import user_tokens
from keyboards.inline_keyboards import (
    build_auth_keyboard,
    build_confirm_delete_keyboard,
    build_edit_habit_keyboard,
    build_habit_actions_keyboard,
    build_habits_list_keyboard,
    build_main_menu_keyboard,
)
from services.api_client import api_client


def build_progress_bar(current: int, target: int) -> str:
    """
    Строит текстовый прогресс-бар из 10 символов.
    Пример: current=7, target=21 → "███░░░░░░░" (7/10 * 10 = 3 заполнено)
    """
    filled = min(int((current / target) * 10), 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty


def require_auth(bot: telebot.TeleBot, message: Message):
    """
    Вспомогательная функция: проверяет авторизацию.
    Если не авторизован — отправляет сообщение и возвращает None.
    Хендлеры вызывают: token = require_auth(bot, message); if token is None: return
    """
    telegram_id = message.from_user.id
    token = user_tokens.get(telegram_id)
    if token is None:
        bot.send_message(
            message.chat.id,
            "Вы не авторизованы. Пожалуйста, войдите.",
            reply_markup=build_auth_keyboard(),
        )
    return token


def register_habits_handlers(bot: telebot.TeleBot) -> None:

    # ── СПИСОК ПРИВЫЧЕК ────────────────────────────────────────────────────────

    @bot.message_handler(func=lambda msg: msg.text == "📋 Мои привычки")
    def handle_show_habits(message: Message) -> None:
        """Кнопка 'Мои привычки' — показывает список активных привычек."""
        token = require_auth(bot, message)
        if token is None:
            return

        result = api_client.get_all_habits(token)
        if result["status_code"] != 200:
            bot.send_message(message.chat.id, "Ошибка при загрузке привычек.")
            return

        habits = result["data"]
        if not habits:
            bot.send_message(
                message.chat.id,
                "У вас пока нет активных привычек.\n"
                "Нажмите '➕ Добавить привычку'!",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        # Считаем: сколько привычек выполнено сегодня
        completed_count = sum(1 for habit in habits if habit.get("is_completed_today"))
        bot.send_message(
            message.chat.id,
            f"📋 Привычки ({completed_count}/{len(habits)} выполнено сегодня):\n\n"
            "Выберите привычку:",
            reply_markup=build_habits_list_keyboard(habits),
        )

    @bot.callback_query_handler(func=lambda call: call.data == "habits_list")
    def handle_habits_list_callback(call: CallbackQuery) -> None:
        """
        Кнопка '◀️ Назад к списку' — обновляет сообщение со списком.
        edit_message_text() — изменяет существующее сообщение (не отправляет новое).
        """
        bot.answer_callback_query(call.id)
        token = user_tokens.get(call.from_user.id)
        if token is None:
            return

        result = api_client.get_all_habits(token)
        if result["status_code"] != 200:
            return

        habits = result["data"]
        if not habits:
            bot.edit_message_text(
                "У вас нет активных привычек.",
                call.message.chat.id,
                call.message.message_id,
            )
            return

        completed_count = sum(1 for habit in habits if habit.get("is_completed_today"))
        bot.edit_message_text(
            f"📋 Привычки ({completed_count}/{len(habits)} выполнено сегодня):\n\n"
            "Выберите привычку:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_habits_list_keyboard(habits),
        )

    # ── ПРОСМОТР ПРИВЫЧКИ ──────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data.startswith("habit_view_"))
    def handle_view_habit(call: CallbackQuery) -> None:
        """
        Нажатие на конкретную привычку в списке.
        callback_data = "habit_view_5" → habit_id = 5
        call.data.split("_")[-1] → берём последний элемент после разбивки по "_"
        """
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        token = user_tokens.get(call.from_user.id)
        if token is None:
            return

        result = api_client.get_all_habits(token)
        if result["status_code"] != 200:
            return

        # Находим нужную привычку по id из полного списка
        found_habit = next(
            (h for h in result["data"] if h["id"] == habit_id), None
        )
        if found_habit is None:
            bot.answer_callback_query(call.id, "Привычка не найдена.")
            return

        status_text = (
            "✅ Выполнено сегодня"
            if found_habit["is_completed_today"]
            else "⭕ Ещё не выполнено"
        )
        progress_bar = build_progress_bar(
            found_habit["total_completions"],
            found_habit["target_completions"],
        )
        habit_text = (
            f"📌 *{found_habit['title']}*\n\n"
            f"{status_text}\n"
            f"Прогресс: {found_habit['total_completions']}/{found_habit['target_completions']} дней\n"
            f"{progress_bar}"
        )
        if found_habit.get("description"):
            habit_text += f"\n\n📄 {found_habit['description']}"

        bot.edit_message_text(
            habit_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=build_habit_actions_keyboard(
                habit_id, found_habit["is_completed_today"]
            ),
        )

    # ── ОТМЕТИТЬ ВЫПОЛНЕННОЙ ──────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data.startswith("habit_done_"))
    def handle_complete_habit(call: CallbackQuery) -> None:
        """Нажатие '✅ Выполнено' — отмечает привычку и обновляет сообщение."""
        habit_id = int(call.data.split("_")[-1])
        token = user_tokens.get(call.from_user.id)
        if token is None:
            return

        result = api_client.complete_habit_today(token, habit_id)
        if result["status_code"] == 200:
            updated_habit = result["data"]
            bot.answer_callback_query(call.id, "Отмечено!")

            if not updated_habit["is_active"]:
                # Привычка выработана! Показываем поздравление
                bot.edit_message_text(
                    f"🎉 *Поздравляем!*\n"
                    f"Привычка *{updated_habit['title']}* выработана!\n\n"
                    f"Выполнено {updated_habit['total_completions']} раз — цель достигнута!",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                )
            else:
                progress_bar = build_progress_bar(
                    updated_habit["total_completions"],
                    updated_habit["target_completions"],
                )
                bot.edit_message_text(
                    f"✅ *{updated_habit['title']}* — выполнено!\n\n"
                    f"Прогресс: {updated_habit['total_completions']}/{updated_habit['target_completions']} дней\n"
                    f"{progress_bar}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=build_habit_actions_keyboard(habit_id, True),
                )
        else:
            bot.answer_callback_query(call.id, "Ошибка. Попробуйте снова.")

    # ── ДОБАВИТЬ ПРИВЫЧКУ ─────────────────────────────────────────────────────

    @bot.message_handler(func=lambda msg: msg.text == "➕ Добавить привычку")
    def handle_add_habit(message: Message) -> None:
        """Начинает диалог создания привычки."""
        token = require_auth(bot, message)
        if token is None:
            return
        bot.send_message(
            message.chat.id,
            "Введите название привычки (например: 'Читать 30 минут'):",
        )
        bot.register_next_step_handler(message, process_habit_title)

    def process_habit_title(message: Message) -> None:
        title = message.text.strip()
        if not title or len(title) > 200:
            bot.send_message(
                message.chat.id,
                "Название должно быть от 1 до 200 символов:",
            )
            bot.register_next_step_handler(message, process_habit_title)
            return
        bot.send_message(
            message.chat.id,
            "Введите описание (или напишите 'нет' для пропуска):",
        )
        bot.register_next_step_handler(message, process_habit_description, title)

    def process_habit_description(message: Message, title: str) -> None:
        description_text = message.text.strip()
        # Если написал "нет" — описания не будет (None)
        description = (
            None
            if description_text.lower() in ("нет", "no", "-", "skip")
            else description_text
        )
        bot.send_message(
            message.chat.id,
            "Сколько раз нужно выполнить для выработки? (по умолчанию 21, или напишите 'ок'):",
        )
        bot.register_next_step_handler(message, process_habit_target, title, description)

    def process_habit_target(message: Message, title: str, description) -> None:
        target_text = message.text.strip().lower()
        target_completions = 21  # значение по умолчанию

        if target_text not in ("ок", "ok", ""):
            try:
                target_completions = int(target_text)
                if not 1 <= target_completions <= 365:
                    raise ValueError("Out of range")
            except ValueError:
                bot.send_message(message.chat.id, "Введите число от 1 до 365 или 'ок':")
                bot.register_next_step_handler(
                    message, process_habit_target, title, description
                )
                return

        token = user_tokens.get(message.from_user.id)
        if token is None:
            return

        result = api_client.create_habit(token, title, description, target_completions)
        if result["status_code"] == 201:
            habit = result["data"]
            bot.send_message(
                message.chat.id,
                f"✅ Привычка *{habit['title']}* добавлена!\nЦель: {habit['target_completions']} раз.",
                parse_mode="Markdown",
                reply_markup=build_main_menu_keyboard(),
            )
        else:
            bot.send_message(
                message.chat.id,
                "Ошибка. Попробуйте снова.",
                reply_markup=build_main_menu_keyboard(),
            )

    # ── УДАЛИТЬ ПРИВЫЧКУ ──────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data.startswith("habit_delete_"))
    def handle_delete_habit_confirm(call: CallbackQuery) -> None:
        """Первый шаг удаления — показывает подтверждение."""
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        bot.edit_message_text(
            "Вы уверены? Это действие нельзя отменить.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_confirm_delete_keyboard(habit_id),
        )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("habit_confirm_delete_")
    )
    def handle_delete_habit_execute(call: CallbackQuery) -> None:
        """Второй шаг — пользователь подтвердил, удаляем."""
        habit_id = int(call.data.split("_")[-1])
        token = user_tokens.get(call.from_user.id)
        if token is None:
            return

        result = api_client.delete_habit(token, habit_id)
        if result["status_code"] == 204:
            bot.answer_callback_query(call.id, "Привычка удалена.")
            bot.edit_message_text(
                "🗑 Привычка удалена.",
                call.message.chat.id,
                call.message.message_id,
            )
        else:
            bot.answer_callback_query(call.id, "Ошибка при удалении.")

    # ── РЕДАКТИРОВАНИЕ ────────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data.startswith("habit_edit_"))
    def handle_edit_habit_menu(call: CallbackQuery) -> None:
        """Показывает меню выбора: что именно редактировать."""
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        bot.edit_message_text(
            "Что хотите изменить?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_edit_habit_keyboard(habit_id),
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_title_"))
    def handle_edit_title(call: CallbackQuery) -> None:
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        sent = bot.send_message(call.message.chat.id, "Введите новое название:")
        bot.register_next_step_handler(sent, process_edit_title, habit_id)

    def process_edit_title(message: Message, habit_id: int) -> None:
        new_title = message.text.strip()
        if not new_title or len(new_title) > 200:
            bot.send_message(message.chat.id, "Название должно быть от 1 до 200 символов.")
            return
        token = user_tokens.get(message.from_user.id)
        if token is None:
            return
        result = api_client.update_habit(token, habit_id, title=new_title)
        if result["status_code"] == 200:
            bot.send_message(
                message.chat.id,
                f"✅ Название: *{new_title}*",
                parse_mode="Markdown",
                reply_markup=build_main_menu_keyboard(),
            )
        else:
            bot.send_message(message.chat.id, "Ошибка при обновлении.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_desc_"))
    def handle_edit_description(call: CallbackQuery) -> None:
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        sent = bot.send_message(
            call.message.chat.id,
            "Введите новое описание (или 'нет' для очистки):",
        )
        bot.register_next_step_handler(sent, process_edit_description, habit_id)

    def process_edit_description(message: Message, habit_id: int) -> None:
        description_text = message.text.strip()
        new_description = (
            " "  # пробел вместо None, чтобы обновить поле
            if description_text.lower() in ("нет", "no", "-")
            else description_text
        )
        token = user_tokens.get(message.from_user.id)
        if token is None:
            return
        result = api_client.update_habit(token, habit_id, description=new_description)
        if result["status_code"] == 200:
            bot.send_message(
                message.chat.id, "✅ Описание обновлено.", reply_markup=build_main_menu_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "Ошибка при обновлении.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_target_"))
    def handle_edit_target(call: CallbackQuery) -> None:
        bot.answer_callback_query(call.id)
        habit_id = int(call.data.split("_")[-1])
        sent = bot.send_message(call.message.chat.id, "Введите новое количество дней (1-365):")
        bot.register_next_step_handler(sent, process_edit_target, habit_id)

    def process_edit_target(message: Message, habit_id: int) -> None:
        try:
            new_target = int(message.text.strip())
            if not 1 <= new_target <= 365:
                raise ValueError
        except ValueError:
            bot.send_message(message.chat.id, "Введите число от 1 до 365.")
            return
        token = user_tokens.get(message.from_user.id)
        if token is None:
            return
        result = api_client.update_habit(token, habit_id, target_completions=new_target)
        if result["status_code"] == 200:
            bot.send_message(
                message.chat.id,
                f"✅ Цель: {new_target} дней.",
                reply_markup=build_main_menu_keyboard(),
            )
        else:
            bot.send_message(message.chat.id, "Ошибка при обновлении.")

    # ── УВЕДОМЛЕНИЯ ───────────────────────────────────────────────────────────

    @bot.message_handler(func=lambda msg: msg.text == "⏰ Настроить уведомление")
    def handle_set_notification(message: Message) -> None:
        token = require_auth(bot, message)
        if token is None:
            return
        bot.send_message(
            message.chat.id,
            "Введите время напоминания в формате ЧЧ:ММ (например: 09:00)\n"
            "Или 'нет' для отключения:",
        )
        bot.register_next_step_handler(message, process_notification_time)

    def process_notification_time(message: Message) -> None:
        time_text = message.text.strip()

        if time_text.lower() in ("нет", "no", "-"):
            notification_time_value = None
        else:
            try:
                parts = time_text.split(":")
                if len(parts) != 2:
                    raise ValueError
                hours, minutes = int(parts[0]), int(parts[1])
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValueError
                # Форматируем в "HH:MM" с ведущими нулями
                notification_time_value = f"{hours:02d}:{minutes:02d}"
            except ValueError:
                bot.send_message(
                    message.chat.id,
                    "Неверный формат. Используйте ЧЧ:ММ (например: 09:00):",
                )
                bot.register_next_step_handler(message, process_notification_time)
                return

        token = user_tokens.get(message.from_user.id)
        if token is None:
            return

        result = api_client.set_notification_time(token, notification_time_value)
        if result["status_code"] == 200:
            if notification_time_value:
                bot.send_message(
                    message.chat.id,
                    f"⏰ Уведомления настроены на {notification_time_value} (UTC).",
                    reply_markup=build_main_menu_keyboard(),
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "🔕 Уведомления отключены.",
                    reply_markup=build_main_menu_keyboard(),
                )
        else:
            bot.send_message(message.chat.id, "Ошибка при сохранении.")