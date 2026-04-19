import telebot
from telebot.types import Message

from handlers.auth_handler import user_tokens
from keyboards.inline_keyboards import build_auth_keyboard, build_main_menu_keyboard


def register_start_handlers(bot: telebot.TeleBot) -> None:

    @bot.message_handler(commands=["start"])
    def handle_start_command(message: Message) -> None:
        """
        /start — первое сообщение пользователя.
        Если уже авторизован → главное меню.
        Если нет → предлагаем войти или зарегистрироваться.
        """
        telegram_id = message.from_user.id

        # Проверяем: есть ли токен для этого пользователя?
        if telegram_id in user_tokens:
            bot.send_message(
                message.chat.id,
                "С возвращением! Выберите действие:",
                reply_markup=build_main_menu_keyboard(),
            )
            return  # выходим из функции, не показываем приветствие

        welcome_text = (
            "Привет! Я бот для трекинга привычек.\n\n"
            "Я помогу вам:\n"
            "• Создавать и отслеживать ежедневные привычки\n"
            "• Отмечать выполнение каждый день\n"
            "• Получать напоминания в нужное время\n"
            "• Выработать привычку за 21 день\n\n"
            "Зарегистрируйтесь или войдите, чтобы начать:"
        )
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=build_auth_keyboard(),  # кнопки Регистрация/Войти
        )

    @bot.message_handler(func=lambda msg: msg.text == "ℹ️ Помощь")
    def handle_help_button(message: Message) -> None:
        """
        Кнопка Помощь.
        func=lambda msg: msg.text == "..." — хендлер срабатывает когда текст равен этой строке.
        parse_mode="Markdown" — поддержка *жирного* текста через звёздочки.
        """
        help_text = (
            "📖 *Справка по боту:*\n\n"
            "📋 *Мои привычки* — список активных привычек с прогрессом\n"
            "➕ *Добавить привычку* — создать новую привычку\n"
            "⏰ *Настроить уведомление* — задать время напоминания\n\n"
            "*Действия с привычкой:*\n"
            "✅ Отметить выполненной сегодня\n"
            "✏️ Изменить название, описание или цель\n"
            "🗑 Удалить привычку\n\n"
            "Привычка исчезает из списка после достижения цели (по умолчанию 21 выполнение)."
        )
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")