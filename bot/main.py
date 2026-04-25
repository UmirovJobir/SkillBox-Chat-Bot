import logging
import sys

import telebot

from config import TELEGRAM_BOT_TOKEN
from handlers.auth_handler import register_auth_handlers, user_tokens
from handlers.habits_handler import register_habits_handlers
from handlers.start_handler import register_start_handlers
from scheduler import setup_scheduler

# Настройка логирования — все INFO сообщения выводятся в stdout
# В Docker их можно смотреть через: docker-compose logs -f bot
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def start_bot() -> None:
    """Инициализирует и запускает Telegram-бот."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан в .env файле!")
        sys.exit(1)

    # telebot.TeleBot — главный класс бота
    # parse_mode=None — не устанавливаем глобальный режим разметки
    # (в некоторых сообщениях мы используем Markdown, в других — нет)
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)

    # Регистрируем хендлеры — порядок имеет значение!
    # Если два хендлера могут совпасть — первый зарегистрированный побеждает
    register_start_handlers(bot)
    register_auth_handlers(bot)
    register_habits_handlers(bot)

    # Запускаем планировщик уведомлений в фоновом потоке
    # user_tokens — тот же словарь, что используют хендлеры (общая ссылка)
    scheduler = setup_scheduler(bot, user_tokens)

    logger.info("Бот запущен и ждёт сообщений...")
    try:
        # infinity_polling — бесконечный цикл опроса Telegram API
        # timeout=10 — таймаут одного запроса к Telegram
        # long_polling_timeout=5 — Telegram держит соединение открытым 5 сек
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except KeyboardInterrupt:
        logger.info("Бот остановлен (Ctrl+C).")
    finally:
        scheduler.shutdown()  # корректно останавливаем планировщик
        logger.info("Планировщик остановлен.")


if __name__ == "__main__":
    start_bot()