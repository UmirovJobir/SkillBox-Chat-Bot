import telebot
from telebot.types import CallbackQuery, Message

from keyboards.inline_keyboards import build_auth_keyboard, build_main_menu_keyboard
from services.api_client import api_client

# ──────────────────────────────────────────────────────────────────────────────
# ХРАНИЛИЩЕ ТОКЕНОВ
# Словарь хранится в памяти процесса. Все хендлеры импортируют ЭТУ же переменную.
# Python модули — синглтоны: при импорте создаётся один экземпляр на весь процесс.
# from handlers.auth_handler import user_tokens  → это та же dict, не копия!
# ──────────────────────────────────────────────────────────────────────────────
user_tokens: dict = {}  # {telegram_id: "eyJhbGc...jwt_token..."}


def register_auth_handlers(bot: telebot.TeleBot) -> None:
    """
    Регистрирует хендлеры аутентификации.
    Вынесено в функцию, чтобы передать экземпляр bot.
    Вызывается один раз в main.py.
    """

    # ── РЕГИСТРАЦИЯ ────────────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == "auth_register")
    def handle_register_button(call: CallbackQuery) -> None:
        """
        Срабатывает когда пользователь нажал кнопку "Регистрация".
        call.data == "auth_register" — это callback_data из build_auth_keyboard().
        bot.answer_callback_query() — убирает "часики" на кнопке (обязательно!).
        """
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "Введите желаемый никнейм (от 3 до 100 символов):",
        )
        # register_next_step_handler — следующее сообщение от этого пользователя
        # будет передано в функцию process_register_username
        bot.register_next_step_handler(call.message, process_register_username)

    def process_register_username(message: Message) -> None:
        """Получает никнейм, проверяет и просит пароль."""
        username = message.text.strip()
        if len(username) < 3 or len(username) > 100:
            bot.send_message(
                message.chat.id,
                "Никнейм должен быть от 3 до 100 символов. Попробуйте снова:",
            )
            # Если валидация не прошла — снова ждём правильный никнейм
            bot.register_next_step_handler(message, process_register_username)
            return
        bot.send_message(message.chat.id, "Введите пароль (минимум 6 символов):")
        # Передаём username в следующий шаг через args
        bot.register_next_step_handler(message, process_register_password, username)

    def process_register_password(message: Message, username: str) -> None:
        """Получает пароль, удаляет сообщение с ним, отправляет на backend."""
        password = message.text.strip()

        # БЕЗОПАСНОСТЬ: удаляем сообщение с паролем из чата
        # Пароль не должен оставаться в истории переписки
        bot.delete_message(message.chat.id, message.message_id)

        if len(password) < 6:
            bot.send_message(
                message.chat.id,
                "Пароль слишком короткий. Минимум 6 символов:",
            )
            bot.register_next_step_handler(
                message, process_register_password, username
            )
            return

        telegram_id = message.from_user.id
        result = api_client.register_user(telegram_id, username, password)

        if result["status_code"] == 201:
            # Успешная регистрация — сохраняем токен
            access_token = result["data"]["access_token"]
            user_tokens[telegram_id] = access_token
            bot.send_message(
                message.chat.id,
                f"Добро пожаловать, {username}! Регистрация прошла успешно.",
                reply_markup=build_main_menu_keyboard(),
            )
        elif result["status_code"] == 409:
            # Конфликт — пользователь или username уже существует
            detail = result["data"].get("detail", "")
            if "Telegram" in detail:
                bot.send_message(
                    message.chat.id,
                    "Вы уже зарегистрированы. Нажмите 'Войти'.",
                    reply_markup=build_auth_keyboard(),
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "Этот никнейм уже занят. Введите другой:",
                )
                bot.register_next_step_handler(message, process_register_username)
        else:
            bot.send_message(
                message.chat.id,
                "Произошла ошибка. Попробуйте позже.",
                reply_markup=build_auth_keyboard(),
            )

    # ── ВХОД ──────────────────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == "auth_login")
    def handle_login_button(call: CallbackQuery) -> None:
        """Кнопка 'Войти' — просим пароль (telegram_id уже есть из call.from_user.id)."""
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Введите ваш пароль:")
        bot.register_next_step_handler(call.message, process_login_password)

    def process_login_password(message: Message) -> None:
        """Получает пароль, удаляет его из чата, отправляет на backend."""
        password = message.text.strip()
        bot.delete_message(message.chat.id, message.message_id)

        telegram_id = message.from_user.id
        result = api_client.login_user(telegram_id, password)

        if result["status_code"] == 200:
            access_token = result["data"]["access_token"]
            user_tokens[telegram_id] = access_token  # сохраняем токен
            bot.send_message(
                message.chat.id,
                "Вы успешно вошли!",
                reply_markup=build_main_menu_keyboard(),
            )
        else:
            bot.send_message(
                message.chat.id,
                "Неверный пароль. Попробуйте снова.",
                reply_markup=build_auth_keyboard(),
            )